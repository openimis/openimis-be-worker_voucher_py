import logging

from core.services import BaseService
from core.signals import register_service_signal
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
