from django.apps import AppConfig

DEFAULT_CONFIG = {
    "gql_worker_voucher_search_perms": ["204001"],
    "gql_worker_voucher_create_perms": ["204002"],
    "gql_worker_voucher_update_perms": ["204003"],
    "gql_worker_voucher_delete_perms": ["204004"],
}


class WorkerVoucherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'worker_voucher'

    gql_worker_voucher_search_perms = None
    gql_worker_voucher_create_perms = None
    gql_worker_voucher_update_perms = None
    gql_worker_voucher_delete_perms = None

    def ready(self):
        from core.models import ModuleConfiguration

        cfg = ModuleConfiguration.get_or_default(self.name, DEFAULT_CONFIG)
        self._load_config(cfg)

    @classmethod
    def _load_config(cls, cfg):
        """
        Load all config fields that match current AppConfig class fields, all custom fields have to be loaded separately
        """
        for field in cfg:
            if hasattr(cls, field):
                setattr(cls, field, cfg[field])
