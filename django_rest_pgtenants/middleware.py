# django_rest_pgtenants/middleware.py

from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django_rest_pgtenants.schema_manager import set_search_path, reset_search_path

class BaseTenantSchemaMiddleware(MiddlewareMixin):
    def get_tenant_model(self):
        config = getattr(settings, 'NATIVE_TENANT', {})
        model_path = config.get('TENANT_MODEL')
        if not model_path:
            raise ValueError("NATIVE_TENANT['TENANT_MODEL'] must be configured in settings.")
        return apps.get_model(model_path)

    def get_schema_column(self):
        config = getattr(settings, 'NATIVE_TENANT', {})
        return config.get('SCHEMA_COLUMN', 'schema_name')

    def get_schema_for_request(self, request) -> str:
        raise NotImplementedError("Subclasses must implement get_schema_for_request")

    def process_request(self, request):
        request.workspace_schema = 'public'
        try:
            schema_name = self.get_schema_for_request(request)
            if schema_name:
                request.workspace_schema = schema_name
                set_search_path(schema_name)
                return
        except Exception:
            pass
        reset_search_path()

    def process_response(self, request, response):
        reset_search_path()
        return response


class JWTWorkspaceSchemaMiddleware(BaseTenantSchemaMiddleware):
    def get_schema_for_request(self, request) -> str:
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            jwt_authenticator = JWTAuthentication()
            header = jwt_authenticator.get_header(request)
            if header is not None:
                raw_token = jwt_authenticator.get_raw_token(header)
                if raw_token is not None:
                    validated_token = jwt_authenticator.get_validated_token(raw_token)
                    user = jwt_authenticator.get_user(validated_token)
                    request.user = user
                    
                    config = getattr(settings, 'NATIVE_TENANT', {})
                    tenant_claim = config.get('TENANT_CLAIM', 'workspace_id')
                    tenant_field = config.get('TENANT_FIELD', 'id')
                    
                    tenant_value = validated_token.get(tenant_claim)
                    if tenant_value:
                        cache_key = f"workspace_schema_{tenant_value}"
                        schema_name = cache.get(cache_key)
                        if not schema_name:
                            TenantModel = self.get_tenant_model()
                            workspace = TenantModel.objects.filter(**{tenant_field: tenant_value}).first()
                            if workspace:
                                schema_column = self.get_schema_column()
                                schema_name = getattr(workspace, schema_column)
                                cache.set(cache_key, schema_name, 3600)
                        return schema_name
        except Exception:
            pass
        return None


class SubdomainSchemaMiddleware(BaseTenantSchemaMiddleware):
    def get_schema_for_request(self, request) -> str:
        try:
            host = request.get_host().split(':')[0]
            parts = host.split('.')
            if len(parts) > 2:
                subdomain = parts[0]
                cache_key = f"workspace_schema_subdomain_{subdomain}"
                schema_name = cache.get(cache_key)
                if not schema_name:
                    TenantModel = self.get_tenant_model()
                    workspace = TenantModel.objects.filter(slug=subdomain).first()
                    if workspace:
                        schema_column = self.get_schema_column()
                        schema_name = getattr(workspace, schema_column)
                        cache.set(cache_key, schema_name, 3600)
                return schema_name
        except Exception:
            pass
        return None


class HeaderTenantSchemaMiddleware(BaseTenantSchemaMiddleware):
    def get_schema_for_request(self, request) -> str:
        try:
            config = getattr(settings, 'NATIVE_TENANT', {})
            header_name = config.get('TENANT_HEADER', 'X-Tenant-ID')
            tenant_field = config.get('TENANT_FIELD', 'id')
            
            tenant_value = request.headers.get(header_name)
            if tenant_value:
                cache_key = f"workspace_schema_header_{tenant_value}"
                schema_name = cache.get(cache_key)
                if not schema_name:
                    TenantModel = self.get_tenant_model()
                    workspace = TenantModel.objects.filter(**{tenant_field: tenant_value}).first()
                    if workspace:
                        schema_column = self.get_schema_column()
                        schema_name = getattr(workspace, schema_column)
                        cache.set(cache_key, schema_name, 3600)
                return schema_name
        except Exception:
            pass
        return None

