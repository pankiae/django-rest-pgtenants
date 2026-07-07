# django_rest_pgtenants/db_routers.py

from django.conf import settings
from django_rest_pgtenants.context import is_running_tenant_migration

class TenantRouter:
    @property
    def tenant_apps(self):
        config = getattr(settings, 'NATIVE_TENANT', {})
        return config.get('TENANT_APPS', [])

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if is_running_tenant_migration():
            # During tenant migration, only migrate the configured tenant apps
            return app_label in self.tenant_apps
        else:
            # During normal migration, block tenant apps
            if app_label in self.tenant_apps:
                return False
        return None
