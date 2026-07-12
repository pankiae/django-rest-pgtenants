# django_rest_pgtenants/management/commands/migrate_tenants.py

from typing import Any, Optional
from django.core.management.base import BaseCommand, CommandParser
from django.apps import apps
from django.conf import settings
from django_rest_pgtenants.schema_manager import run_migrations_on_schema

class Command(BaseCommand):
    """
    Django management command to apply database migrations across all configured tenant schemas.
    """
    help = 'Run Django migrations across all tenant schemas.'

    def add_arguments(self, parser: CommandParser) -> None:
        """
        Define the command-line arguments accepted by this command.

        Args:
            parser (CommandParser): The parser instance used to declare arguments.
        """
        parser.add_argument(
            '--target',
            type=str,
            default=None,
            help='Target migration to migrate/rollback to (e.g. 0001 or "zero" to rollback all).'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Execute the migration commands across all active tenant schemas.

        Args:
            *args (Any): Variable length argument list.
            **options (Any): Arbitrary keyword arguments containing parsed options.
        """
        config: dict = getattr(settings, 'NATIVE_TENANT', {})
        model_path: Optional[str] = config.get('TENANT_MODEL')
        schema_column: str = config.get('SCHEMA_COLUMN', 'schema_name')
        
        if not model_path:
            self.stdout.write(self.style.ERROR("NATIVE_TENANT['TENANT_MODEL'] is not configured in settings."))
            return
            
        TenantModel = apps.get_model(model_path)
        tenants = TenantModel.objects.all()
        self.stdout.write(f"Found {tenants.count()} tenants to migrate.")
        
        target = options.get('target')
        for tenant in tenants:
            schema_name = getattr(tenant, schema_column)
            target_str = f" to target '{target}'" if target else " to latest"
            self.stdout.write(f"Migrating schema '{schema_name}' for tenant '{tenant}'{target_str}...")
            try:
                run_migrations_on_schema(schema_name, target_migration=target)
                self.stdout.write(self.style.SUCCESS(f"Successfully migrated schema '{schema_name}'."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating schema '{schema_name}': {e}"))
                
        self.stdout.write(self.style.SUCCESS("All migrations completed successfully!"))

