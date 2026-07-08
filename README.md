# django-rest-pgtenants

A lightweight, native multi-tenancy package for PostgreSQL schema isolation, purpose-built for **Django REST Framework (DRF) APIs** and asynchronous background workers (like Celery). Unlike other packages, it requires zero database engine overrides, monkeypatching, or custom database backends.

---

## 🚀 Features

* **Native Django Approach**: Zero monkeypatching. It runs entirely on Django's official database routing and middleware API.
* **REST API First**: Pluggable middlewares for JWT/OIDC token claims and custom HTTP headers.
* **Thread & Async Safe**: Uses Python's native `contextvars.ContextVar` instead of `threading.local`, preventing context leaking across concurrent async requests or workers.
* **Fail-Safe Security**: Tenant-specific tables are never created in the shared `public` schema. Any query executed without a tenant context will instantly fail with `relation does not exist` instead of leaking global data.
* **Automatic Cache Flushing**: Automatically flushes Django's internal `ContentType` and permission cache on every schema switch to prevent cross-tenant permission leakages.
* **Worker & Script Support**: A clean, context-manager wrapper `tenant_context` for background tasks, scripts, and shell commands.
* **Granular Tenant Migrations**: A robust `migrate_tenants` command supporting forward migrations, target migration rollbacks, and database zero-state resets.

---

## 🛠️ The Core Concept

In PostgreSQL, a single database can contain multiple isolated **schemas** (namespaces):
* **`public` schema**: Stores shared/global tables (like your tenant catalog, global users, Django metadata).
* **Tenant schemas** (e.g. `tenant_acme`, `tenant_apple`): Store tenant-specific data tables (e.g. projects, orders, members).

For every request, the middleware dynamically switches PostgreSQL's `search_path`:
```sql
SET search_path TO tenant_schema, public;
```
PostgreSQL will search for tables inside the tenant schema first, falling back to the `public` schema only if the table is not found.

---

## 📦 Installation

Install the package via `pip` (or add it to your `requirements.txt`):

```bash
pip install django-rest-pgtenants
```

---

## ⚙️ Configuration

### 1. Update `settings.py`

Register the package, database router, and define the apps isolated inside the schemas:

```python
INSTALLED_APPS = [
    # Django core apps...
    'django.contrib.contenttypes',
    'django.contrib.auth',
    
    # Pluggable multi-tenancy
    'django_rest_pgtenants',
    
    # Your shared apps (e.g. global workspaces catalog)
    'api.workspaces',
    
    # Your tenant-specific apps (tables inside individual tenant schemas)
    'api.workspace_tenant',
]

# Register the database router
DATABASE_ROUTERS = ['django_rest_pgtenants.db_routers.TenantRouter']

# Configure django-rest-pgtenants settings
NATIVE_TENANT = {
    'TENANT_MODEL': 'workspaces.Workspace',          # Model storing tenant metadata (app_label.ModelName)
    'SCHEMA_COLUMN': 'schema_name',                  # Column storing the PostgreSQL schema name
    'TENANT_APPS': ['api.workspace_tenant'],         # Apps that should only exist inside tenant schemas
    
    # Pluggable Middleware Configuration (Optional)
    'TENANT_CLAIM': 'workspace_id',                  # JWT claim key to extract tenant value
    'TENANT_FIELD': 'id',                            # Model field on TENANT_MODEL to query the value against
    'TENANT_HEADER': 'X-Tenant-ID',                  # Request header to extract tenant value
}
```

### 2. Choose and Register Middleware

Select the routing strategy that fits your project and add it to `MIDDLEWARE` in `settings.py`:

#### Option A: JWT / Token-based Routing (API-First)
Decodes incoming JWT tokens, parses the tenant claim, and switches search paths.
```python
MIDDLEWARE = [
    ...
    'django_rest_pgtenants.middleware.JWTWorkspaceSchemaMiddleware',
    ...
]
```

#### Option B: Subdomain-based Routing
Extracts subdomains (e.g., `acme.example.com` -> `acme`) and matches it to a tenant slug.
```python
MIDDLEWARE = [
    ...
    'django_rest_pgtenants.middleware.SubdomainSchemaMiddleware',
    ...
]
```

#### Option C: Custom HTTP Header Routing
Resolves schemas by reading a specific HTTP request header (e.g., `X-Tenant-ID`).
```python
MIDDLEWARE = [
    ...
    'django_rest_pgtenants.middleware.HeaderTenantSchemaMiddleware',
    ...
]
```

---

## 📖 Component Overview

### 1. Database Router (`django_rest_pgtenants/db_routers.py`)
Intercepts Django migrations. It blocks tenant-specific tables from being created in the `public` schema during regular `python manage.py migrate` commands. Tenant migrations must run through the custom runner command.

### 2. Schema Manager (`django_rest_pgtenants/schema_manager.py`)
Handles dynamic SQL schema creation, `search_path` switches, and exposes the tenant switching API.

### 3. Context Manager for Workers (`Celery`)
To write safe asynchronous tasks or background jobs, wrap your logic inside `tenant_context`:

```python
from celery import shared_task
from django_rest_pgtenants.schema_manager import tenant_context
from api.workspace_tenant.models import WorkspaceMember

@shared_task
def process_workspace_reports(schema_name):
    # Switches search_path safely for this worker thread context block
    with tenant_context(schema_name):
        members = WorkspaceMember.objects.all()  # Queries the tenant's schema tables
        # ... process report
```

---

## 🗄️ Running Migrations

### Public / Shared Schema Migrations
Run standard Django migrations for all shared apps (e.g. custom user profiles, billing/tenant records):
```bash
python manage.py migrate
```

### Tenant Schema Migrations
To migrate all tenant schemas to the latest database migrations:
```bash
python manage.py migrate_tenants
```

#### Rolling Back a Migration
To rollback all tenants to a specific migration target (e.g., version `0002` or `zero` to rollback all tenant tables):
```bash
python manage.py migrate_tenants --target 0002
python manage.py migrate_tenants --target zero
```

---

## 🔒 Connection Pooling Safety

When using connection poolers like PgBouncer or Django's persistent connections (`CONN_MAX_AGE`), a database connection is reused for multiple HTTP requests. 

`django-rest-pgtenants` automatically resets the search path:
1. When a request starts, search path switches to: `schema_name, public`
2. At the end of the request-response cycle (even if the view crashes), it resets the search path back to: `public`

This prevents a subsequent request from accidentally inheriting the database schema context of a previous tenant.

---

## 📄 License
This project is licensed under the MIT License.