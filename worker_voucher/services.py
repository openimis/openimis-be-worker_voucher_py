import logging
import pandas as pd
from io import BytesIO
from decimal import Decimal
from typing import Iterable, Dict, Union, List
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet, UUIDField, Count
from django.db.models.functions import Cast
from django.utils.translation import gettext as _

from core import datetime
from core.models import InteractiveUser, User
from core.services import BaseService
from core.services.utils import (
    output_exception,
    model_representation,
    output_result_success
)
from core.signals import register_service_signal
from insuree.models import Insuree
from insuree.gql_mutations import update_or_create_insuree
from invoice.models import Bill
from invoice.services import BillService
from policyholder.models import PolicyHolder, PolicyHolderInsuree
from policyholder.services import PolicyHolderInsuree as PolicyHolderInsureeService
from msystems.services.mconnect_worker_service import MConnectWorkerService
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import WorkerVoucher, GroupOfWorker, WorkerGroup
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
        assigned_date__date=today,
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


def get_group_worker_user_filters(user: InteractiveUser) -> Iterable[Q]:
    return [Q(
        policyholder__policyholderuser__user__i_user=user.i_user,
        policyholder__is_deleted=False,
        policyholder__policyholderuser__is_deleted=False,
        policyholder__policyholderuser__user__validity_to__isnull=True,
        policyholder__policyholderuser__user__i_user__validity_to__isnull=True,
    )] if not user.has_perms(WorkerVoucherConfig.gql_group_of_worker_search_all_perms) else []


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
        insurees = _check_insurees(workers, eu_code, user)
        insurees_count = len(insurees)
        dates = _check_dates(date_ranges)
        vouchers_per_insuree_count = len(dates)
        check_existing_active_vouchers(ph, insurees, dates)
        for insuree in insurees:
            years = {date.year for date in dates}
            for year in years:
                count = sum(1 for d in dates if d.year == year)
                _check_voucher_limit(insuree, user, ph, year, count)
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
        insurees = _check_insurees(workers, eu_code, user)
        insurees_count = len(insurees)
        dates = _check_dates(date_ranges)
        vouchers_per_insuree_count = len(dates)
        for insuree in insurees:
            years = {date.year for date in dates}
            for year in years:
                count = sum(1 for d in dates if d.year == year)
                _check_voucher_limit(insuree, user, ph, year, count)
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
        return PolicyHolder.objects.get(
            economic_unit_user_filter(user, economic_unit_code=eu_code)
        )
    except PolicyHolder.DoesNotExist:
        raise VoucherException(_(f"Economic unit {eu_code} does not exists"))


def _check_insurees(workers: List[str], eu_code: str, user: User):
    insurees = set()
    for code in workers:
        try:
            ins = Insuree.objects.get(
                worker_user_filter(user, economic_unit_code=eu_code),
                chf_id=code,
                validity_to__isnull=True,
            )
        except Insuree.DoesNotExist:
            raise VoucherException(_(f"Worker {code} does not exists"))
        if ins in insurees:
            raise VoucherException(_(f"Duplicate worker: {code}"))
        else:
            insurees.add(ins)
    if not insurees:
        raise VoucherException(_("No valid workers"))
    return insurees


def _check_voucher_limit(insuree, user, policyholder, year, count=1):
    voucher_counts = get_worker_yearly_voucher_count_counts(insuree, user, year)

    if voucher_counts.get(policyholder.code, 0) + count > WorkerVoucherConfig.yearly_worker_voucher_limit:
        raise VoucherException(_(f"Worker {insuree.chf_id} reached yearly voucher limit"))


def _check_dates(date_ranges: List[Dict]):
    max_date = _get_voucher_expiry_date(datetime.date.today())
    dates = set()
    for date_range in date_ranges:
        start_date, end_date = (datetime.date.from_ad_date(date_range.get("start_date")),
                                datetime.date.from_ad_date(date_range.get("end_date")))
        if start_date < datetime.date.today():
            raise VoucherException(_(f"Date {start_date} is in the past"))
        if start_date > end_date:
            raise VoucherException(_(f"Start date {start_date} is after end date {end_date}"))

        day_count = (end_date - start_date).days + 1
        for date in (start_date + datetime.datetimedelta(days=n) for n in
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

def _get_voucher_expiry_date(start_date: datetime):
    expiry_type = WorkerVoucherConfig.voucher_expiry_type

    if expiry_type == "end_of_year":
        expiry_date = datetime.datetime(start_date.year, 12, 31, 23, 59, 59)
    elif expiry_type == "fixed_period":
        expiry_period = WorkerVoucherConfig.voucher_expiry_period
        expiry_date = datetime.datetime.today() + datetime.datetimedelta(**expiry_period)
    else:
        raise VoucherException(_("Invalid voucher expiry type"))

    return expiry_date


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


def get_worker_yearly_voucher_count_counts(insuree: Insuree, user: User, year):
    res = WorkerVoucher.objects.filter(
        economic_unit_user_filter(user, prefix="policyholder__"),
        is_deleted=False,
        status__in=(WorkerVoucher.Status.ASSIGNED, WorkerVoucher.Status.AWAITING_PAYMENT),
        insuree=insuree,
        assigned_date__year=year
    ).values("policyholder__code").annotate(count=Count("id"))

    return {row["policyholder__code"]: row["count"] for row in res}


def create_assigned_voucher(user, date, insuree_id, policyholder_id):
    current_date = datetime.datetime.today()
    expiry_date = _get_voucher_expiry_date(current_date)

    voucher_service = WorkerVoucherService(user)
    service_result = voucher_service.create({
        "policyholder_id": policyholder_id,
        "insuree_id": insuree_id,
        "code": str(uuid4()),
        "assigned_date": date,
        "expiry_date": expiry_date
    })
    if service_result.get("success", True):
        return service_result.get("data").get("id")
    else:
        raise VoucherException(service_result["error"])


def create_unassigned_voucher(user, policyholder_id):
    current_date = datetime.date.today()
    expiry_date = _get_voucher_expiry_date(current_date)

    voucher_service = WorkerVoucherService(user)
    service_result = voucher_service.create({
        "policyholder_id": policyholder_id,
        "code": str(uuid4()),
        "expiry_date": expiry_date
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


class WorkerUploadService:
    def __init__(self, user: InteractiveUser):
        self.user = user

    def upload_worker(self, economic_unit_code, file, upload):
        error_column = WorkerVoucherConfig.csv_worker_upload_errors_column
        chf_id_type_column = WorkerVoucherConfig.worker_upload_chf_id_type
        economic_unit = self._resolve_economic_unit(economic_unit_code)
        upload.policyholder = economic_unit
        upload.status = upload.Status.IN_PROGRESS
        upload.save(username=self.user.login_name)
        if not file:
            raise ValueError(_('File is required'))
        df = self._read_file(file)
        self._validate_dataframe(df)

        affected_rows = 0
        skipped_items = 0
        total_number_of_records_in_file = len(df)

        df[error_column] = (
            df.apply(lambda row: self._upload_record_with_worker(economic_unit, row), axis=1)
        )

        for _, row in df.iterrows():
            if not pd.isna(row[error_column]):
                skipped_items += 1
            else:
                affected_rows += 1

        summary = {
            'affected_rows': affected_rows,
            'total_number_of_records_in_file': total_number_of_records_in_file,
            'skipped_items': skipped_items
        }

        error_df = df[df[error_column].apply(lambda x: bool(x))]
        if not error_df.empty:
            in_memory_file = BytesIO()
            df.to_csv(in_memory_file, index=False)
            return (
                in_memory_file,
                error_df.set_index(chf_id_type_column)[error_column].to_dict(),
                summary
            )
        return file, None, summary

    def _read_file(self, file):
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        elif file.name.endswith(('.xls', '.xlsx')):
            return pd.read_excel(file, engine='openpyxl')
        else:
            raise ValueError(_('Unsupported file format. Please upload a CSV or Excel file.'))

    def _validate_dataframe(self, df):
        if df is None:
            raise ValueError(_("Unknown error while loading import file"))
        if df.empty:
            raise ValueError(_("Import file is empty"))
        if WorkerVoucherConfig.csv_worker_upload_errors_column in df.columns:
            raise ValueError(_("Column errors in csv."))
        if WorkerVoucherConfig.worker_upload_chf_id_type not in df.columns:
            raise ValueError(_("No national id column in csv file"))

    def _resolve_economic_unit(self, economic_unit_code):
        if not economic_unit_code:
            raise ValueError('worker_upload.validation.economic_unit_code_required')
        economic_unit = PolicyHolder.objects.filter(code=economic_unit_code, is_deleted=False).first()
        if not economic_unit:
            raise ValueError('worker_upload.validation.economic_unit_not_found')
        return economic_unit

    def _upload_record_with_worker(self, economic_unit, row):
        errors = []
        user_policyholders = PolicyHolder.objects.filter(
            economic_unit_user_filter(self.user)).values_list('id', flat=True)
        chf_id = row[WorkerVoucherConfig.worker_upload_chf_id_type]
        ph = PolicyHolder.objects.filter(
            id=economic_unit.id,
            is_deleted=False,
        ).first()
        if not ph:
            errors.append({"message": _("worker_upload.validation.economic_unit_not_exist")})
        if ph.id not in user_policyholders:
            errors.append({
                "message": _("worker_upload.validation.no_authority_to_use_selected_economic_unit")
            })
        data_from_mconnect = self._fetch_data_from_mconnect(chf_id, ph)
        is_mconnect_success = data_from_mconnect.get("success", False)
        print(is_mconnect_success)
        if not is_mconnect_success:
            errors.append(data_from_mconnect)
        else:
            self._add_worker_to_system(chf_id, economic_unit, data_from_mconnect, errors)
        return errors if errors else None

    def _fetch_data_from_mconnect(self, chf_id, policyholder):
        data_from_mconnect = {}
        if WorkerVoucherConfig.validate_created_worker_online:
            online_result = MConnectWorkerService().fetch_worker_data(chf_id, self.user, policyholder)
            print(online_result)
            if not online_result.get("success", False):
                return online_result
            else:
                data_from_mconnect['chf_id'] = chf_id
                data_from_mconnect['other_names'] = online_result["data"]["GivenName"]
                data_from_mconnect['last_name'] = online_result["data"]["FamilyName"]
                data_from_mconnect['dob'] = online_result["data"]["DateOfBirth"]
                data_from_mconnect['photo'] = {"photo": online_result["data"]["Photo"]}
        return data_from_mconnect

    def _add_worker_to_system(self, chf_id, economic_unit, data_from_mconnect, errors):
        phi = PolicyHolderInsuree.objects.filter(
            insuree__chf_id=chf_id,
            policy_holder__code=economic_unit.code,
            is_deleted=False,
        ).first()
        if not phi:
            worker = Insuree.objects.filter(chf_id=chf_id).first()
            if not worker:
                data_from_mconnect['audit_user_id'] = self.user.id_for_audit
                from core.utils import TimeUtils
                data_from_mconnect['validity_from'] = TimeUtils.now()
                try:
                    worker = update_or_create_insuree(data_from_mconnect, self.user)
                except Exception as e:
                    errors.append({"success": False, "error": str(e)})
            if worker:
                worker = Insuree.objects.filter(chf_id=chf_id).first()
                policy_holder_insuree_service = PolicyHolderInsureeService(self.user)
                policy_holder = PolicyHolder.objects.get(code=economic_unit.code, is_deleted=False)
                policy_holder_insuree = {
                    'policy_holder_id': f'{policy_holder.id}',
                    'insuree_id': worker.id,
                    'contribution_plan_bundle_id': None,
                }
                policy_holder_insuree_service.create(policy_holder_insuree)
        else:
            errors.append({"message": _("workers.validation.worker_already_assigned_to_unit")})
        return errors


class GroupOfWorkerService(BaseService):
    OBJECT_TYPE = GroupOfWorker

    def __init__(self, user, validation_class=None):
        super().__init__(user, validation_class)

    @register_service_signal('group_of_worker_service.create_or_update')
    def create_or_update(self, obj_data, eu_code):
        try:
            with transaction.atomic():
                import datetime
                now = datetime.datetime.now()
                group_id = obj_data.pop('id') if 'id' in obj_data else None
                insurees_chf_id = obj_data.pop('insurees_chf_id') if "insurees_chf_id" in obj_data else None
                insurees = _check_insurees(insurees_chf_id, eu_code, self.user) if len(insurees_chf_id) > 0 else set()
                if group_id:
                    group = GroupOfWorker.objects.get(id=group_id)
                    if group.name != obj_data['name']:
                        if GroupOfWorker.objects.filter(name=obj_data['name'], is_deleted=False).count() > 0:
                            raise ValidationError(_("This name for group already exists."))
                        [setattr(group, k, v) for k, v in obj_data.items()]
                        group.save(user=self.user)
                    if insurees is not None:
                        worker_group_currently_assigned = WorkerGroup.objects.filter(group=group_id)
                        worker_group_currently_assigned.delete()
                        for insuree in insurees:
                            worker_group = WorkerGroup(
                                group_id=group_id,
                                insuree_id=insuree.id,
                            )
                            worker_group.save(user=self.user)
                else:
                    if GroupOfWorker.objects.filter(name=obj_data['name'], is_deleted=False).count() > 0:
                        raise ValidationError(_("This name for group already exists."))
                    group = GroupOfWorker(**obj_data)
                    group.save(user=self.user)
                    if insurees:
                        for insuree in insurees:
                            worker_group = WorkerGroup(
                                **{
                                    "group_id": group.id,
                                    "insuree_id": insuree.id
                                }
                            )
                            worker_group.save(user=self.user)
                dict_repr = model_representation(group)
                return output_result_success(dict_representation=dict_repr)
        except Exception as exc:
            return output_exception(model_name=self.OBJECT_TYPE.__name__, method="create_or_update", exception=exc)

    @register_service_signal('group_of_worker_service.create')
    def create(self, obj_data):
        raise NotImplementedError()

    @register_service_signal('group_of_worker_service.update')
    def update(self, obj_data):
        raise NotImplementedError()

    @register_service_signal('group_of_worker_service.delete')
    def delete(self, group_id, eu_uuid):
        try:
            with transaction.atomic():
                gow = GroupOfWorker.objects.filter(
                    id=group_id,
                    policyholder__uuid=eu_uuid,
                    policyholder__is_deleted=False,
                    is_deleted=False,
                ).first()

                if not gow:
                    return [{"message": _("worker_voucher.validation.group_of_worker_not_exists"), "detail": group_id}]

                worker_group = WorkerGroup.objects.filter(
                    group__id=group_id,
                    group__policyholder__uuid=eu_uuid,
                    group__policyholder__is_deleted=False,
                    is_deleted=False,
                )
                worker_group.delete()
                gow.delete(user=self.user)
                return []
        except Exception as exc:
            return output_exception(model_name=self.OBJECT_TYPE.__name__, method="delete", exception=exc)


def worker_voucher_bill_user_filter(qs: QuerySet, user: User) -> QuerySet:
    if user.is_imis_admin:
        return qs

    user_policyholders = PolicyHolder.objects.filter(
        economic_unit_user_filter(user)).values_list('id', flat=True)

    return qs.annotate(subject_uuid=Cast('subject_id', UUIDField())) \
        .filter(subject_uuid__in=user_policyholders)
