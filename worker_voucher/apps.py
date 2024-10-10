from django.apps import AppConfig

from core.utils import ConfigUtilMixin

DEFAULT_CONFIG = {
    "gql_worker_voucher_search_perms": ["204001"],
    "gql_worker_voucher_create_perms": ["204002"],
    "gql_worker_voucher_update_perms": ["204003"],
    "gql_worker_voucher_delete_perms": ["204004"],
    "gql_worker_voucher_search_all_perms": ["204005"],
    "gql_worker_voucher_acquire_unassigned_perms": ["204006"],
    "gql_worker_voucher_acquire_assigned_perms": ["204007"],
    "gql_worker_voucher_assign_vouchers_perms": ["204008"],
    "unassigned_voucher_enabled": True,
    "price_per_voucher": "100.00",
    "max_generic_vouchers": 1000,
    #  This fileds should be a valid datetimedelata input
    "voucher_bill_due_period": {
        "days": 14
    },
    "voucher_expiry_period": {
        "months": 1
    },
    # voucher_expiry_type = "fixed_period" or "end_of_year"
    "voucher_expiry_type": "end_of_year",
    "yearly_worker_voucher_limit": 120,
    "validate_created_worker_online": False,
    "csv_worker_upload_errors_column": "errors",
    "worker_upload_chf_id_type": "national_id"
}


class WorkerVoucherConfig(AppConfig, ConfigUtilMixin):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'worker_voucher'

    gql_worker_voucher_search_perms = None
    gql_worker_voucher_create_perms = None
    gql_worker_voucher_update_perms = None
    gql_worker_voucher_delete_perms = None
    gql_worker_voucher_search_all_perms = None
    gql_worker_voucher_acquire_unassigned_perms = None
    gql_worker_voucher_acquire_assigned_perms = None
    gql_worker_voucher_assign_vouchers_perms = None

    unassigned_voucher_enabled = None
    price_per_voucher = None
    max_generic_vouchers = None
    voucher_bill_due_period = None
    voucher_expiry_period = None
    voucher_expiry_type = None
    yearly_worker_voucher_limit = None
    validate_created_worker_online = None
    csv_worker_upload_errors_column = None
    worker_upload_chf_id_type = None

    def ready(self):
        from core.models import ModuleConfiguration

        cfg = ModuleConfiguration.get_or_default(self.name, DEFAULT_CONFIG)
        self._load_config_fields(cfg)

    @staticmethod
    def get_worker_upload_payment_file_path(economic_unit_code, file_name=None):
        if file_name:
            return f"csv_worker_upload/economic_unit_{economic_unit_code}/{file_name}"
        return f"csv_worker_upload/economic_unit_{economic_unit_code}"

