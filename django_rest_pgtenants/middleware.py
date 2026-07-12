# django_rest_pgtenants/middleware.py

from typing import Any, Optional, Type
from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.db.models import Model
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django_rest_pgtenants.schema_manager import set_search_path, reset_search_path

class BaseTenantSchemaMiddleware(MiddlewareMixin):
    """
    Base middleware class for routing requests to tenant-specific database schemas.

    Subclasses must implement `get_schema_for_request` to resolve the schema
    associated with each incoming request.
    """

    def get_tenant_model(self) -> Type[Model]:
        """
        Retrieve the configured Django Model class representing tenants.

        Returns:
            Type[Model]: The tenant Django Model class.

        Raises:
            ValueError: If NATIVE_TENANT['TENANT_MODEL'] is not configured in settings.
        """
        config: dict = getattr(settings, 'NATIVE_TENANT', {})
        model_path: Optional[str] = config.get('TENANT_MODEL')
        if not model_path:
            raise ValueError("NATIVE_TENANT['TENANT_MODEL'] must be configured in settings.")
        return apps.get_model(model_path)

    def get_schema_column(self) -> str:
        """
        Retrieve the database column/attribute name that stores the schema name on the tenant model.

        Returns:
            str: The field/column name (defaults to 'schema_name').
        """
        config: dict = getattr(settings, 'NATIVE_TENANT', {})
        return config.get('SCHEMA_COLUMN', 'schema_name')

    def get_schema_for_request(self, request: HttpRequest) -> Optional[str]:
        """
        Resolve and return the schema name for the given HTTP request.

        This method must be implemented by subclasses.

        Args:
            request (HttpRequest): The incoming Django HTTP request.

        Returns:
            Optional[str]: The name of the schema if resolved, or None.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement get_schema_for_request")

    def process_request(self, request: HttpRequest) -> None:
        """
        Intercept the request to set the active tenant database schema (search_path).

        Args:
            request (HttpRequest): The incoming Django HTTP request.
        """
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

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Reset the active schema search path to 'public' after the request finishes.

        Args:
            request (HttpRequest): The Django HTTP request.
            response (HttpResponse): The Django HTTP response.

        Returns:
            HttpResponse: The unmodified Django HTTP response.
        """
        reset_search_path()
        return response


class JWTWorkspaceSchemaMiddleware(BaseTenantSchemaMiddleware):
    """
    Middleware that identifies the tenant schema based on a claim in a SimpleJWT token.
    """

    def get_schema_for_request(self, request: HttpRequest) -> Optional[str]:
        """
        Resolve the tenant schema name from a JWT bearer token.

        Uses Rest Framework SimpleJWT to extract the token, extract the tenant claim,
        and look up the corresponding schema from the cache or tenant model.

        Args:
            request (HttpRequest): The incoming Django HTTP request.

        Returns:
            Optional[str]: The resolved tenant schema name, or None if not found/invalid.
        """
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
                    
                    config: dict = getattr(settings, 'NATIVE_TENANT', {})
                    tenant_claim: str = config.get('TENANT_CLAIM', 'workspace_id')
                    tenant_field: str = config.get('TENANT_FIELD', 'id')
                    
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
    """
    Middleware that identifies the tenant schema based on the request's subdomain.
    """

    def get_schema_for_request(self, request: HttpRequest) -> Optional[str]:
        """
        Resolve the tenant schema name using the host's subdomain.

        Args:
            request (HttpRequest): The incoming Django HTTP request.

        Returns:
            Optional[str]: The resolved tenant schema name, or None if not found/invalid.
        """
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
    """
    Middleware that identifies the tenant schema based on an HTTP header.
    """

    def get_schema_for_request(self, request: HttpRequest) -> Optional[str]:
        """
        Resolve the tenant schema name from a specific HTTP header.

        Args:
            request (HttpRequest): The incoming Django HTTP request.

        Returns:
            Optional[str]: The resolved tenant schema name, or None if not found/invalid.
        """
        try:
            config: dict = getattr(settings, 'NATIVE_TENANT', {})
            header_name: str = config.get('TENANT_HEADER', 'X-Tenant-ID')
            tenant_field: str = config.get('TENANT_FIELD', 'id')
            
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


