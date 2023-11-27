from core.validation import BaseModelValidation
from worker_voucher.models import WorkerVoucher


class WorkerVoucherValidation(BaseModelValidation):
    OBJECT_TYPE = WorkerVoucher
