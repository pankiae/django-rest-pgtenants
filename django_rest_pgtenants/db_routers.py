# django_rest_pgtenants/db_routers.py

from typing import List, Any, Optional
from django.conf import settings
from django_rest_pgtenants.context import is_running_tenant_migration

class TenantRouter:
    """
    Database router to steer migrations and database operations appropriately
    between tenant-specific schemas and the public schema.
    """

    @property
    def tenant_apps(self) -> List[str]:
        """
        Retrieve the list of application labels that are designated as tenant-specific apps.

        Returns:
            List[str]: A list of app label strings configured in settings under NATIVE_TENANT['TENANT_APPS'].
        """
        config: dict = getattr(settings, 'NATIVE_TENANT', {})
        return config.get('TENANT_APPS', [])

    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, **hints: Any) -> Optional[bool]:
        """
        Determine if a migration is allowed to run on a given database/schema for an app.

        During tenant migrations, only tenant-specific apps are allowed to migrate.
        During public/standard migrations, tenant-specific apps are blocked from migrating.

        Args:
            db (str): The alias of the database being migrated.
            app_label (str): The label of the app being migrated.
            model_name (Optional[str]): The name of the model being migrated. Defaults to None.
            **hints (Any): Additional context hints for the migration.

        Returns:
            Optional[bool]: True to allow, False to deny, or None to let other routers decide.
        """
        if is_running_tenant_migration():
            # During tenant migration, only migrate the configured tenant apps
            return app_label in self.tenant_apps
        else:
            # During normal migration, block tenant apps
            if app_label in self.tenant_apps:
                return False
        return None

