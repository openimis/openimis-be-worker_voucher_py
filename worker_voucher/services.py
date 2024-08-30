import logging
from decimal import Decimal
from typing import Iterable, Dict, Union, List
from uuid import uuid4

from django.db import transaction
from django.db.models import Q, QuerySet, UUIDField
from django.db.models.functions import Cast
from django.utils.translation import gettext as _

from core import datetime
from core.models import InteractiveUser, User
from core.services import BaseService
from core.signals import register_service_signal
from insuree.models import Insuree
from invoice.models import Bill
from invoice.services import BillService
from policyholder.models import PolicyHolder
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import WorkerVoucher
from worker_voucher.validation import WorkerVoucherValidation

logger = logging.getLogger(__name__)


class VoucherException(Exception):
    pass


class WorkerVoucherService(BaseService):
    OBJECT_TYPE = WorkerVoucher

    def __init__(self, user, validation_class=WorkerVoucherValidation):
        super().__init__(user, validation_class)

    @register_service_signal('worker_voucher_service.create')
    def create(self, obj_data):
        return super().create(obj_data)

    @register_service_signal('worker_voucher_service.update')
    def update(self, obj_data):
        return super().update(obj_data)

    @register_service_signal('worker_voucher_service.delete')
    def delete(self, obj_data):
        return super().delete(obj_data)


def get_voucher_worker_enquire_filters(national_id: str) -> Iterable[Q]:
    today = datetime.datetime.now()

    return [Q(
        insuree__chf_id=national_id,
        insuree__validity_to__isnull=True,
        policyholder__is_deleted=False,
        is_deleted=False,
        status=WorkerVoucher.Status.ASSIGNED,
        assigned_date=today,
        expiry_date__gte=today,
    )]


def get_voucher_user_filters(user: InteractiveUser) -> Iterable[Q]:
    return [Q(
        policyholder__policyholderuser__user__i_user=user,
        policyholder__is_deleted=False,
        policyholder__policyholderuser__is_deleted=False,
        policyholder__policyholderuser__user__validity_to__isnull=True,
        policyholder__policyholderuser__user__i_user__validity_to__isnull=True,
    )] if not user.user.has_perms(WorkerVoucherConfig.gql_worker_voucher_search_all_perms) else []


def validate_acquire_unassigned_vouchers(user: User, eu_code: str, count: Union[int, str]) -> Dict:
    try:
        price_per_voucher = Decimal(WorkerVoucherConfig.price_per_voucher)
        ph = _check_ph(user, eu_code)

        count = int(count)
        if count < 1:
            return {"success": False,
                    "error": _("Count have to be greater than 0"), }
        if count > WorkerVoucherConfig.max_generic_vouchers:
            return {"success": False,
                    "error": _("Max voucher count exceeded"), }
        return {
            "success": True,
            "data": {
                "policyholder": ph,
                "count": count,
                "price_per_voucher": price_per_voucher,
                "price": price_per_voucher * count
            }
        }
    except VoucherException as e:
        return {"success": False, "error": str(e)}


def validate_acquire_assigned_vouchers(user: User, eu_code: str, workers: List[str], date_ranges: List[Dict]):
    try:
        price_per_voucher = Decimal(WorkerVoucherConfig.price_per_voucher)
        ph = _check_ph(user, eu_code)
        insurees = _check_insurees(workers)
        insurees_count = len(insurees)
        dates = _check_dates(date_ranges)
        vouchers_per_insuree_count = len(dates)
        check_existing_active_vouchers(ph, insurees, dates)
        for insuree in insurees:
            _check_voucher_limit(insuree, vouchers_per_insuree_count)
        count = insurees_count * vouchers_per_insuree_count
        return {
            "success": True,
            "data": {
                "policyholder": ph,
                "insurees": insurees,
                "dates": dates,
                "count": count,
                "price_per_voucher": price_per_voucher,
                "price": price_per_voucher * count
            }
        }
    except VoucherException as e:
        return {"success": False, "error": str(e)}


def validate_assign_vouchers(user: User, eu_code: str, workers: List[str], date_ranges: List[Dict]):
    try:
        ph = _check_ph(user, eu_code)
        insurees = _check_insurees(workers)
        insurees_count = len(insurees)
        dates = _check_dates(date_ranges)
        vouchers_per_insuree_count = len(dates)
        for insuree in insurees:
            _check_voucher_limit(insuree, vouchers_per_insuree_count)
        check_existing_active_vouchers(ph, insurees, dates)
        count = insurees_count * vouchers_per_insuree_count
        unassigned_vouchers = _check_unassigned_vouchers(ph, dates, count)
        return {
            "success": True,
            "data": {
                "policyholder": ph,
                "insurees": insurees,
                "dates": dates,
                "unassigned_vouchers": list(unassigned_vouchers),
                "count": count,
                "price_per_voucher": Decimal("0"),
                "price": Decimal("0")
            }
        }
    except VoucherException as e:
        return {"success": False, "error": str(e)}


def _check_ph(user: User, eu_code: str):
    try:
        return PolicyHolder.objects.get(code=eu_code, is_deleted=False, policyholderuser__user=user,
                                        policyholderuser__is_deleted=False)
    except PolicyHolder.DoesNotExist:
        raise VoucherException(_(f"Economic unit {eu_code} does not exists"))


def _check_insurees(workers: List[str]):
    insurees = set()
    for code in workers:
        try:
            ins = Insuree.objects.get(chf_id=code, validity_to__isnull=True)
        except Insuree.DoesNotExist:
            raise VoucherException(_(f"Worker {code} does not exists"))
        if ins in insurees:
            raise VoucherException(_(f"Duplicate worker: {code}"))
        else:
            insurees.add(ins)
    if not insurees:
        raise VoucherException(_("No valid workers"))
    return insurees


def _check_voucher_limit(insuree, count=1):
    if get_worker_yearly_voucher_count(insuree.id) + count > WorkerVoucherConfig.yearly_worker_voucher_limit:
        raise VoucherException(_(f"Worker {insuree.chf_id} reached yearly voucher limit"))


def _check_dates(date_ranges: List[Dict]):
    expiry_period = WorkerVoucherConfig.voucher_expiry_period
    max_date = datetime.date.today() + datetime.datetimedelta(**expiry_period)
    dates = set()
    for date_range in date_ranges:
        start_date, end_date = date_range.get("start_date"), date_range.get("end_date")
        day_count = (end_date - start_date).days + 1
        for date in (datetime.date.from_ad_date(start_date) + datetime.datetimedelta(days=n) for n in
                     range(day_count)):
            if date in dates:
                raise VoucherException(_(f"Date {date} in more than one range"))
            if date > max_date:
                raise VoucherException(_(f"Date {date} after voucher expiry date"))
            else:
                dates.add(date)
    if not dates:
        raise VoucherException(_(f"No valid dates"))
    return dates


def check_existing_active_vouchers(ph, insurees, dates):
    if isinstance(dates, set):
        date_filter = {'assigned_date__in': dates}
    else:
        date_filter = {'assigned_date__gte': dates}

    if WorkerVoucher.objects.filter(
            insuree__in=insurees,
            policyholder=ph,
            status__in=(WorkerVoucher.Status.ASSIGNED, WorkerVoucher.Status.AWAITING_PAYMENT),
            is_deleted=False,
            **date_filter
    ).exists():
        raise VoucherException(_("One or more workers have assigned vouchers in specified ranges"))


def _check_unassigned_vouchers(ph, dates, count):
    #  Naive approach, all unassigned vouchers have to be valid for the whole range
    #  instead of their respective assigned date
    unassigned_vouchers = WorkerVoucher.objects.filter(
        insuree=None,
        assigned_date=None,
        expiry_date__gte=max(dates),
        policyholder=ph,
        status=WorkerVoucher.Status.UNASSIGNED,
        is_deleted=False).order_by('expiry_date')[:count]
    if unassigned_vouchers.count() < count:
        raise VoucherException(_(f"Not enough unassigned vouchers"))
    return unassigned_vouchers


def get_worker_yearly_voucher_count(insuree_id):
    return WorkerVoucher.objects.filter(
        is_deleted=False,
        status__in=(WorkerVoucher.Status.ASSIGNED, WorkerVoucher.Status.AWAITING_PAYMENT),
        insuree_id=insuree_id,
        assigned_date__year=datetime.datetime.now().year
    ).count()


def create_assigned_voucher(user, date, insuree_id, policyholder_id):
    expiry_period = WorkerVoucherConfig.voucher_expiry_period
    voucher_service = WorkerVoucherService(user)
    service_result = voucher_service.create({
        "policyholder_id": policyholder_id,
        "insuree_id": insuree_id,
        "code": str(uuid4()),
        "assigned_date": date,
        "expiry_date": datetime.datetime.now() + datetime.datetimedelta(**expiry_period)
    })
    if service_result.get("success", True):
        return service_result.get("data").get("id")
    else:
        raise VoucherException(service_result["error"])


def create_unassigned_voucher(user, policyholder_id):
    expiry_period = WorkerVoucherConfig.voucher_expiry_period
    voucher_service = WorkerVoucherService(user)
    service_result = voucher_service.create({
        "policyholder_id": policyholder_id,
        "code": str(uuid4()),
        "expiry_date": datetime.datetime.now() + datetime.datetimedelta(**expiry_period)
    })
    if service_result.get("success", False):
        return service_result.get("data").get("id")
    else:
        raise VoucherException(service_result["error"])


def assign_voucher(user, insuree_id, voucher_id, assigned_date):
    # This service function does not check if the voucher is eligible to be assigned
    voucher_service = WorkerVoucherService(user)
    service_result = voucher_service.update({
        "id": voucher_id,
        "insuree_id": insuree_id,
        "assigned_date": assigned_date,
        "status": WorkerVoucher.Status.ASSIGNED
    })
    if service_result.get("success", True):
        service_result.get("data").get("id")
    else:
        raise VoucherException(service_result["error"])


def create_voucher_bill(user, voucher_ids, policyholder_id):
    bill_due_period = WorkerVoucherConfig.voucher_bill_due_period

    bill_data = {
        'subject_type': "policyholder",
        'subject_id': policyholder_id,
        'code': str(uuid4()),
        'status': Bill.Status.VALIDATED,
        'date_due': datetime.datetime.now() + datetime.datetimedelta(**bill_due_period)
    }

    bill_data_line = []

    with transaction.atomic():
        for voucher_id in voucher_ids:
            voucher = WorkerVoucher.objects.get(id=voucher_id)
            price = Decimal(WorkerVoucherConfig.price_per_voucher)
            bill_data_line.append({
                "code": str(uuid4()),
                "description": f"Voucher {voucher.code}",
                "line_type": "workervoucher",
                "line_id": voucher_id,
                "quantity": 1,
                "unit_price": price,
                "amount_net": price,
                "amount_total": price,
            })

        bill_create_payload = {
            "user": user,
            "bill_data": bill_data,
            "bill_data_line": bill_data_line
        }

        return BillService.bill_create(convert_results=bill_create_payload)


def economic_unit_user_filter(user: User, economic_unit_code=None, prefix='') -> Q:
    filters = {
        f'{prefix}is_deleted': False
    }

    if not user.is_imis_admin and not user.has_perms(WorkerVoucherConfig.gql_worker_voucher_search_all_perms):
        filters = {
            **filters,
            f'{prefix}policyholderuser__user': user,
            f'{prefix}policyholderuser__is_deleted': False,
            f'{prefix}policyholderuser__user__validity_to__isnull': True,
            f'{prefix}policyholderuser__user__i_user__validity_to__isnull': True,
            f'{prefix}is_deleted': False
        }

    if economic_unit_code:
        filters = {
            **filters,
            f'{prefix}code': economic_unit_code
        }

    return Q(**filters)


def worker_user_filter(user: User, economic_unit_code=None, prefix='') -> Q:
    filters = {
        f'{prefix}validity_to__isnull': True
    }

    if not user.is_imis_admin and not user.has_perms(WorkerVoucherConfig.gql_worker_voucher_search_all_perms):
        filters = {
            **filters,
            f"{prefix}policyholderinsuree__is_deleted": False,
        }
        return Q(**filters) & economic_unit_user_filter(user,
                                                        economic_unit_code=economic_unit_code,
                                                        prefix="policyholderinsuree__policy_holder__")
    else:
        if economic_unit_code:
            filters = {
                **filters,
                f"{prefix}policyholderinsuree__is_deleted": False,
                f"{prefix}policyholderinsuree__policy_holder__is_deleted": False,
                f"{prefix}policyholderinsuree__policy_holder__code": economic_unit_code,
            }
        return Q(**filters)


def worker_voucher_bill_user_filter(qs: QuerySet, user: User) -> QuerySet:
    if user.is_imis_admin:
        return qs

    user_policyholders = PolicyHolder.objects.filter(
        economic_unit_user_filter(user)).values_list('id', flat=True)

    return qs.annotate(subject_uuid=Cast('subject_id', UUIDField())) \
        .filter(subject_uuid__in=user_policyholders)
