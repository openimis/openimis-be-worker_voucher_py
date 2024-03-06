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
    "unassigned_voucher_enabled": False,
    "price_per_voucher": "100.00",
    "max_generic_vouchers": 1000,
    #  This filed should be a valid datetimedelata input
    "voucher_expiry_period": {
        "months": 1
    }
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
    voucher_expiry_period = None

    def ready(self):
        from core.models import ModuleConfiguration

        cfg = ModuleConfiguration.get_or_default(self.name, DEFAULT_CONFIG)
        self._load_config_fields(cfg)
