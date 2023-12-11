import logging
from decimal import Decimal
from typing import Iterable, Dict, Union, List
from django.db.models import Q
from django.utils.translation import gettext as _

from core import datetime
from core.models import InteractiveUser, User
from core.services import BaseService
from core.signals import register_service_signal
from insuree.models import Insuree
from policyholder.models import PolicyHolder
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import WorkerVoucher
from worker_voucher.validation import WorkerVoucherValidation

logger = logging.getLogger(__name__)


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


def validate_acquire_unassigned_voucher(user: User, eu_code: str, count: Union[int, str]) -> Dict:
    try:
        price_per_voucher = Decimal(WorkerVoucherConfig.price_per_voucher)
        try:
            ph = PolicyHolder.objects.get(code=eu_code, is_deleted=False, policyholderuser__user=user,
                                          policyholderuser__is_deleted=False)
        except PolicyHolder.DoesNotExist:
            return {"success": False,
                    "error": _(f"Economic unit {eu_code} does not exists"), }
        count = int(count)
        if count < 1:
            raise AttributeError(_("Count have to be greater than 0"))
        return {
            "success": True,
            "data": {
                "policyholder": ph,
                "count": count,
                "price_per_voucher": price_per_voucher,
                "price": price_per_voucher * count
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def validate_acquire_assigned_voucher(user: User, eu_code: str, workers: List[str], date_ranges: List[Dict]):
    try:
        price_per_voucher = Decimal(WorkerVoucherConfig.price_per_voucher)
        try:
            ph = PolicyHolder.objects.get(code=eu_code, is_deleted=False, policyholderuser__user=user,
                                          policyholderuser__is_deleted=False)
        except PolicyHolder.DoesNotExist:
            return {"success": False,
                    "error": _(f"Economic unit {eu_code} does not exists"), }
        insurees = set()
        for code in workers:
            try:
                ins = Insuree.objects.get(chf_id=code, validity_to__isnull=True)
            except Insuree.DoesNotExist:
                return {"success": False,
                        "error": _(f"Worker {code} does not exists"), }
            if ins in insurees:
                raise Exception(_(f"Duplicate worker: {code}"))
            else:
                insurees.add(ins)
        dates = set()
        for date_range in date_ranges:
            start_date, end_date = date_range.get("start_date"), date_range.get("end_date")
            day_count = (end_date - start_date).days + 1
            for date in (datetime.date.from_ad_date(start_date) + datetime.datetimedelta(days=n) for n in
                         range(day_count)):
                if date in dates:
                    raise Exception(_(f"Date {date} in more than one range"))
                else:
                    dates.add(date)
        if WorkerVoucher.objects.filter(
                insuree__in=insurees,
                assigned_date__in=dates,
                policyholder=ph,
                status__in=(WorkerVoucher.Status.ASSIGNED, WorkerVoucher.Status.AWAITING_PAYMENT),
                is_deleted=False).exists():
            raise Exception(_("One or more workers have assigned vouchers in specified ranges"))
        count = len(insurees) * len(dates)
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
    except Exception as e:
        return {"success": False, "error": str(e)}
