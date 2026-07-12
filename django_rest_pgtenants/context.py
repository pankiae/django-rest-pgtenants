# django_rest_pgtenants/context.py

from contextvars import ContextVar

# Context variables that are safe for both threads and async execution tasks
_running_tenant_migration = ContextVar('running_tenant_migration', default=False)
_active_schema = ContextVar('active_schema', default='public')

def is_running_tenant_migration() -> bool:
    """
    Check if a tenant migration is currently running in the active execution context.

    Returns:
        bool: True if a tenant migration is in progress; False otherwise.
    """
    return _running_tenant_migration.get()

def set_running_tenant_migration(val: bool) -> None:
    """
    Set the tenant migration status for the active execution context.

    Args:
        val (bool): True if tenant migrations are running, False otherwise.
    """
    _running_tenant_migration.set(val)

def get_active_schema() -> str:
    """
    Retrieve the name of the active tenant schema in the current execution context.

    Returns:
        str: The active schema name (defaults to 'public').
    """
    return _active_schema.get()

def set_active_schema(schema_name: str) -> None:
    """
    Set the active tenant schema name for the current execution context.

    Args:
        schema_name (str): The name of the schema to activate.
    """
    _active_schema.set(schema_name)

