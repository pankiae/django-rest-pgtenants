# django_rest_pgtenants/context.py

from contextvars import ContextVar

# Context variables that are safe for both threads and async execution tasks
_running_tenant_migration = ContextVar('running_tenant_migration', default=False)
_active_schema = ContextVar('active_schema', default='public')

def is_running_tenant_migration() -> bool:
    return _running_tenant_migration.get()

def set_running_tenant_migration(val: bool):
    _running_tenant_migration.set(val)

def get_active_schema() -> str:
    return _active_schema.get()

def set_active_schema(schema_name: str):
    _active_schema.set(schema_name)
