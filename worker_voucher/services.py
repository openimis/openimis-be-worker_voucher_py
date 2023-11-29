import logging
from typing import Iterable

from core import datetime
from core.models import InteractiveUser
from core.services import BaseService
from core.signals import register_service_signal
from django.db.models import Q

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
