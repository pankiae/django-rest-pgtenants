# django_rest_pgtenants/schema_manager.py

import re
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django_rest_pgtenants.context import set_running_tenant_migration, set_active_schema

from django.contrib.contenttypes.models import ContentType

from contextlib import contextmanager

def validate_schema_name(schema_name):
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema_name):
        raise ValueError(f"Invalid schema name: {schema_name}")

def set_search_path(schema_name):
    validate_schema_name(schema_name)
    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {schema_name}, public;")
    try:
        ContentType.objects.clear_cache()
    except Exception:
        pass
    set_active_schema(schema_name)

def reset_search_path():
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO public;")
    try:
        ContentType.objects.clear_cache()
    except Exception:
        pass
    set_active_schema('public')

@contextmanager
def tenant_context(schema_name):
    validate_schema_name(schema_name)
    try:
        set_search_path(schema_name)
        yield
    finally:
        reset_search_path()

def run_migrations_on_schema(schema_name, target_migration=None):
    validate_schema_name(schema_name)
    
    config = getattr(settings, 'NATIVE_TENANT', {})
    tenant_apps = config.get('TENANT_APPS', [])
    
    set_running_tenant_migration(True)
    try:
        # 1. Route to the tenant schema search path
        set_search_path(schema_name)
        
        # 2. Ensure django_migrations table exists in this schema
        recorder = MigrationRecorder(connection)
        recorder.ensure_schema()
        
        # 3. Synchronize public migrations to this tenant schema's tracker
        # so Django knows public-schema dependencies are already satisfied.
        tenant_apps_set = set(tenant_apps)
        with connection.cursor() as cursor:
            # Copy all migrations except the ones belonging to tenant apps
            placeholders = ", ".join(["%s"] * len(tenant_apps))
            query = f"""
                INSERT INTO django_migrations (app, name, applied)
                SELECT pm.app, pm.name, pm.applied 
                FROM public.django_migrations pm
                WHERE pm.app NOT IN ({placeholders})
                  AND NOT EXISTS (
                      SELECT 1 FROM django_migrations tm 
                      WHERE tm.app = pm.app AND tm.name = pm.name
                  );
            """
            cursor.execute(query, list(tenant_apps))
        
        # 4. Initialize Executor
        executor = MigrationExecutor(connection)
        graph = executor.loader.graph
        
        # 5. Resolve targets for all tenant apps
        targets = []
        for app in tenant_apps:
            if target_migration is not None:
                target_str = str(target_migration).strip()
                if target_str.lower() == 'zero':
                    targets.append((app, None))
                else:
                    matched = [
                        m[1] for m in graph.nodes 
                        if m[0] == app and m[1].startswith(target_str)
                    ]
                    if matched:
                        targets.append((app, matched[0]))
                    else:
                        # If target not matched for this app, but it is the main app, we can raise
                        # otherwise just ignore.
                        pass
            else:
                # Add all leaf nodes for this app
                for leaf_app, leaf_name in graph.leaf_nodes():
                    if leaf_app == app:
                        targets.append((leaf_app, leaf_name))
        
        # 6. Run the migrations
        if targets:
            executor.migrate(targets)
        
    except Exception as e:
        reset_search_path()
        raise RuntimeError(f"Error migrating schema '{schema_name}': {e}") from e
    finally:
        reset_search_path()
        set_running_tenant_migration(False)

def create_workspace_schema(schema_name):
    validate_schema_name(schema_name)
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
    run_migrations_on_schema(schema_name)

def drop_workspace_schema(schema_name):
    validate_schema_name(schema_name)
    with connection.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")
