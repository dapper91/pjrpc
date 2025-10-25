"""
OpenAPI Specification generator. See https://swagger.io/specification/.
"""

import dataclasses as dc
from collections import defaultdict
from typing import Any, Callable, Iterable, Mapping, Optional, Union

from pjrpc.common import UNSET, MaybeSet, UnsetType, exceptions
from pjrpc.server import Method, utils
from pjrpc.server.specs import Specification
from pjrpc.server.specs.extractors import BaseMethodInfoExtractor
from pjrpc.server.specs.schemas import build_request_schema, build_response_schema

from .spec import ApiKeyLocation, Components, Contact, Encoding, ExampleObject, ExternalDocumentation, Header, Info
from .spec import Json, JsonSchema, License, Link, MediaType, MethodExample, OAuthFlow, OAuthFlows, Operation
from .spec import Parameter, ParameterLocation, Path, Reference, RequestBody, Response, SecurityScheme
from .spec import SecuritySchemeType, Server, ServerVariable, SpecRoot, StyleType, Tag

__all__ = [
    'ApiKeyLocation',
    'Components',
    'Contact',
    'Encoding',
    'ExampleObject',
    'ExternalDocumentation',
    'Header',
    'Info',
    'Json',
    'JsonSchema',
    'License',
    'Link',
    'MediaType',
    'metadata',
    'MethodExample',
    'MethodMetadata',
    'OAuthFlow',
    'OAuthFlows',
    'OpenAPI',
    'Operation',
    'Parameter',
    'ParameterLocation',
    'Path',
    'Reference',
    'RequestBody',
    'Response',
    'SecurityScheme',
    'SecuritySchemeType',
    'Server',
    'ServerVariable',
    'SpecRoot',
    'StyleType',
    'Tag',
]


HTTP_DEFAULT_STATUS = 200
JSONRPC_MEDIATYPE = 'application/json'


def drop_unset(obj: Any) -> Any:
    if isinstance(obj, dict):
        return dict((drop_unset(k), drop_unset(v)) for k, v in obj.items() if k is not UNSET and v is not UNSET)
    if isinstance(obj, (tuple, list, set)):
        return list(drop_unset(v) for v in obj if v is not UNSET)

    return obj


MethodType = Callable[..., Any]


class OpenAPI(Specification):
    """
    OpenAPI Specification.

    :param info: provides metadata about the API
    :param servers: an array of Server Objects, which provide connectivity information to a target server
    :param external_docs: additional external documentation
    :param openapi: the semantic version number of the OpenAPI Specification version that the OpenAPI document uses
    :param json_schema_dialect: the default value for the $schema keyword within Schema Objects
    :param tags: a list of tags used by the specification with additional metadata
    :param security: a declaration of which security mechanisms can be used across the API
    :param security_schemes: an object to hold reusable Security Scheme Objects
    """

    def __init__(
        self,
        info: Info,
        servers: MaybeSet[list[Server]] = UNSET,
        external_docs: MaybeSet[ExternalDocumentation] = UNSET,
        tags: MaybeSet[list[Tag]] = UNSET,
        security: MaybeSet[list[dict[str, list[str]]]] = UNSET,
        security_schemes: MaybeSet[dict[str, Union[SecurityScheme, Reference]]] = UNSET,
        openapi: str = '3.1.0',
        json_schema_dialect: MaybeSet[str] = UNSET,
    ):
        self._info = info
        self._servers = servers
        self._external_docs = external_docs
        self._tags = tags
        self._security = security
        self._security_schemes = security_schemes
        self._openapi = openapi
        self._json_schema_dialect = json_schema_dialect

    def generate(self, root_endpoint: str, methods: Mapping[str, Iterable[Method]]) -> dict[str, Any]:
        spec_root = SpecRoot(
            info=self._info,
            paths={},
            components=Components(securitySchemes=self._security_schemes),
            servers=self._servers,
            externalDocs=self._external_docs,
            tags=self._tags,
            security=self._security,
            openapi=self._openapi,
            jsonSchemaDialect=self._json_schema_dialect,
        )
        spec_root.components.schemas = {}

        methods_list = [(path, method) for path, methods in methods.items() for method in methods]
        for endpoint, method in methods_list:
            path = utils.join_path(root_endpoint, endpoint)
            for meta in method.metadata:
                if isinstance(meta, MethodSpecification):
                    spec_root.paths[f'{path}#{method.name}'] = Path(post=meta.operation)
                    spec_root.components.schemas.update(meta.component_schemas or {})

        return drop_unset(dc.asdict(spec_root))


@dc.dataclass(frozen=True)
class MethodMetadata:
    params_schema: MaybeSet[dict[str, JsonSchema]] = UNSET
    result_schema: MaybeSet[JsonSchema] = UNSET
    examples: MaybeSet[list[MethodExample]] = UNSET
    tags: MaybeSet[list[Tag]] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    external_docs: MaybeSet[ExternalDocumentation] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    security: MaybeSet[list[dict[str, list[str]]]] = UNSET
    parameters: MaybeSet[list[Parameter]] = UNSET
    servers: MaybeSet[list[Server]] = UNSET
    component_name_prefix: MaybeSet[str] = UNSET
    errors: MaybeSet[list[type[exceptions.TypedError]]] = UNSET

    def merge(self, other: 'MethodMetadata') -> 'MethodMetadata':
        return MethodMetadata(
            params_schema=self.params_schema if self.params_schema is not UNSET else other.params_schema,
            result_schema=self.result_schema if self.result_schema is not UNSET else other.result_schema,
            summary=self.summary if self.summary is not UNSET else other.summary,
            description=self.description if self.description is not UNSET else other.description,
            external_docs=self.external_docs if self.external_docs is not UNSET else other.external_docs,
            deprecated=self.deprecated if self.deprecated is not UNSET else other.deprecated,
            component_name_prefix=self.component_name_prefix if self.component_name_prefix is not UNSET
            else other.component_name_prefix,
            examples=((self.examples or []) + (other.examples or [])) or UNSET,
            tags=((self.tags or []) + (other.tags or [])) or UNSET,
            security=((self.security or []) + (other.security or [])) or UNSET,
            parameters=((self.parameters or []) + (other.parameters or [])) or UNSET,
            servers=((self.servers or []) + (other.servers or [])) or UNSET,
            errors=((self.errors or []) + (other.errors or [])) or UNSET,
        )


def metadata(
    params_schema: MaybeSet[dict[str, JsonSchema]] = UNSET,
    result_schema: MaybeSet[JsonSchema] = UNSET,
    errors: MaybeSet[list[type[exceptions.TypedError]]] = UNSET,
    examples: MaybeSet[list[MethodExample]] = UNSET,
    tags: MaybeSet[list[Union[str, Tag]]] = UNSET,
    summary: MaybeSet[str] = UNSET,
    description: MaybeSet[str] = UNSET,
    external_docs: MaybeSet[ExternalDocumentation] = UNSET,
    deprecated: MaybeSet[bool] = UNSET,
    security: MaybeSet[list[dict[str, list[str]]]] = UNSET,
    parameters: MaybeSet[list[Parameter]] = UNSET,
    servers: MaybeSet[list[Server]] = UNSET,
    component_name_prefix: MaybeSet[str] = UNSET,
) -> MethodMetadata:
    """
    Adds Open Api specification annotation to the method.

    :param params_schema: method parameters JSON schema
    :param result_schema: method result JSON schema
    :param errors: method errors
    :param examples: method usage examples
    :param tags: a list of tags for method documentation control
    :param summary: a short summary of what the method does
    :param description: a verbose explanation of the method behavior
    :param external_docs: an external resource for extended documentation
    :param deprecated: declares this method to be deprecated
    :param security: a declaration of which security mechanisms can be used for the method
    :param parameters: a list of parameters that are applicable for the method
    :param servers: a list of connectivity information of a target server.
    :param component_name_prefix: components name prefix.
    """

    return MethodMetadata(
        params_schema=params_schema,
        result_schema=result_schema,
        examples=examples,
        tags=[
            tag if isinstance(tag, Tag) else Tag(name=tag) for tag in tags
        ] if not isinstance(tags, UnsetType) else UNSET,
        summary=summary,
        description=description,
        external_docs=external_docs,
        deprecated=deprecated,
        security=security,
        parameters=parameters,
        servers=servers,
        component_name_prefix=component_name_prefix,
        errors=errors,
    )


@dc.dataclass(frozen=True)
class MethodSpecification:
    operation: Operation
    component_schemas: MaybeSet[dict[str, JsonSchema]] = UNSET


class MethodSpecificationGenerator:
    def __init__(self, extractor: BaseMethodInfoExtractor, error_http_status_map: Optional[dict[int, int]] = None):
        self._extractor = extractor
        self._error_http_status_map = error_http_status_map or {}

    def __call__(self, method: Method) -> Method:
        method_metadata = MethodMetadata()
        for meta in method.metadata:
            if isinstance(meta, MethodMetadata):
                method_metadata = method_metadata.merge(meta)

        method_specification = self._generate(method.func, method.name, method_metadata)
        method.metadata.append(method_specification)

        return method

    def _generate(self, method: MethodType, method_name: str, method_metadata: MethodMetadata) -> MethodSpecification:
        status_errors_map = self._extract_errors(method, method_metadata)
        default_status_errors = status_errors_map.pop(HTTP_DEFAULT_STATUS, [])

        component_schemas: dict[str, JsonSchema] = {}

        request_schema, request_components = self._extract_request_schema(method, method_name, method_metadata)
        component_schemas.update(request_components)

        errors_schema, errors_components = self._extract_errors_schema(
            method, method_name, method_metadata, status_errors_map,
        )
        component_schemas.update(errors_components)

        response_schema, response_components = self._extract_response_schema(
            method, method_name, method_metadata, default_status_errors,
        )
        component_schemas.update(response_components)

        request_examples, response_success_examples = self._build_examples(method_name, method_metadata.examples or [])

        tags = method_metadata.tags or []
        servers = method_metadata.servers
        parameters = method_metadata.parameters or []
        security = method_metadata.security
        external_docs = method_metadata.external_docs

        if method_metadata.summary is UNSET:
            summary = self._extractor.extract_summary(method)
        else:
            summary = method_metadata.summary

        if method_metadata.description is UNSET:
            description = self._extractor.extract_description(method)
        else:
            description = method_metadata.description

        if method_metadata.deprecated is UNSET:
            deprecated = self._extractor.extract_deprecation_status(method)
        else:
            deprecated = method_metadata.deprecated

        return MethodSpecification(
            operation=Operation(
                requestBody=RequestBody(
                    description='JSON-RPC Request',
                    content={
                        JSONRPC_MEDIATYPE: MediaType(
                            schema=request_schema,
                            examples=request_examples or UNSET,
                        ),
                    },
                    required=True,
                ),
                responses={
                    **{
                        str(HTTP_DEFAULT_STATUS): Response(
                            description=(response_schema or {}).get('description', 'JSON-RPC Response'),
                            content={
                                JSONRPC_MEDIATYPE: MediaType(
                                    schema=response_schema,
                                    examples=response_success_examples or UNSET,
                                ),
                            },
                        ),
                    },
                    **{
                        str(status): Response(
                            description=error_schema.get('description', 'JSON-RPC Error'),
                            content={
                                JSONRPC_MEDIATYPE: MediaType(
                                    schema=error_schema,
                                ),
                            },
                        )
                        for status, error_schema in errors_schema.items()
                    },
                },
                tags=[tag.name for tag in tags] or UNSET,
                summary=summary,
                description=description,
                deprecated=deprecated,
                externalDocs=external_docs,
                security=security or UNSET,
                parameters=list(parameters) or UNSET,
                servers=servers or UNSET,
            ),
            component_schemas=component_schemas or UNSET,
        )

    def _extract_errors(
        self,
        method: MethodType,
        method_metadata: MethodMetadata,
    ) -> dict[int, list[type[exceptions.TypedError]]]:
        errors = (method_metadata.errors or []) + (self._extractor.extract_errors(method) or [])

        status_error_map: dict[int, list[type[exceptions.TypedError]]] = defaultdict(list)
        unique_errors = list({error.CODE: error for error in errors}.values())
        for error in unique_errors:
            http_status = self._error_http_status_map.get(error.CODE, HTTP_DEFAULT_STATUS)
            status_error_map[http_status].append(error)

        return status_error_map

    def _extract_errors_schema(
        self,
        method: MethodType,
        method_name: str,
        method_metadata: MethodMetadata,
        status_errors_map: dict[int, list[type[exceptions.TypedError]]],
    ) -> tuple[dict[int, dict[str, Any]], dict[str, JsonSchema]]:
        status_error_schema_map: dict[int, dict[str, Any]] = {}
        component_schemas: dict[str, JsonSchema] = {}
        component_name_prefix = method_metadata.component_name_prefix or f"{method.__module__}_"

        for status, errors in status_errors_map.items():
            if result := self._extractor.extract_error_response_schema(
                method_name,
                method,
                ref_template=f'#/components/schemas/{component_name_prefix}{{model}}',
                errors=errors,
            ):
                error_schema, error_component_schemas = result
                if error_component_schemas:
                    component_schemas.update({
                        f"{component_name_prefix}{name}": component
                        for name, component in error_component_schemas.items()
                    })
                status_error_schema_map[status] = error_schema

        return status_error_schema_map, component_schemas

    def _extract_request_schema(
        self,
        method: MethodType,
        method_name: str,
        method_metadata: MethodMetadata,
    ) -> tuple[MaybeSet[dict[str, Any]], dict[str, JsonSchema]]:
        component_schemas: dict[str, JsonSchema] = {}
        component_name_prefix = method_metadata.component_name_prefix or f"{method.__module__}_"

        request_schema: MaybeSet[dict[str, Any]] = UNSET
        if params_schema := method_metadata.params_schema:
            request_schema = build_request_schema(method_name, params_schema)
        else:
            if result := self._extractor.extract_request_schema(
                method_name,
                method,
                ref_template=f'#/components/schemas/{component_name_prefix}{{model}}',
            ):
                request_schema, request_components = result
                if request_components:
                    component_schemas.update({
                        f"{component_name_prefix}{name}": component
                        for name, component in request_components.items()
                    })

        return request_schema, component_schemas

    def _extract_response_schema(
        self,
        method: MethodType,
        method_name: str,
        method_metadata: MethodMetadata,
        errors: list[type[exceptions.TypedError]],
    ) -> tuple[MaybeSet[dict[str, Any]], dict[str, JsonSchema]]:
        component_schemas: dict[str, JsonSchema] = {}
        component_name_prefix = method_metadata.component_name_prefix or f"{method.__module__}_"

        response_schema: MaybeSet[dict[str, Any]] = UNSET
        if result_schema := method_metadata.result_schema:
            response_schema = build_response_schema(result_schema, errors=errors)
        else:
            if result := self._extractor.extract_response_schema(
                method_name,
                method,
                ref_template=f'#/components/schemas/{component_name_prefix}{{model}}',
                errors=errors,
            ):
                response_schema, response_components = result
                if response_components:
                    component_schemas.update({
                        f"{component_name_prefix}{name}": component
                        for name, component in response_components.items()
                    })

        return response_schema, component_schemas

    def _build_examples(self, method_name: str, examples: list[MethodExample]) -> tuple[dict[str, Any], dict[str, Any]]:
        request_examples: dict[str, Any] = {
            example.summary or f'Example#{i}': ExampleObject(
                summary=example.summary,
                description=example.description,
                value={
                    'jsonrpc': example.version,
                    'id': 1,
                    'method': method_name,
                    'params': example.params,
                },
            ) for i, example in enumerate(examples)
        }

        response_examples: dict[str, Any] = {
            example.summary or f'Example#{i}': ExampleObject(
                summary=example.summary,
                description=example.description,
                value={
                    'jsonrpc': example.version,
                    'id': 1,
                    'result': example.result,
                },
            ) for i, example in enumerate(examples)
        }

        return request_examples, response_examples
