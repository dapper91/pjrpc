"""
OpenAPI Specification generator. See https://swagger.io/specification/.
"""

try:
    import dataclasses as dc
except ImportError:
    raise AssertionError("python 3.7 or later is required")

import copy
import enum
import functools as ft
import pathlib
import re
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Type, TypedDict, Union

from pjrpc.common import UNSET, MaybeSet, UnsetType, exceptions
from pjrpc.common.typedefs import Func
from pjrpc.server import Method, utils
from pjrpc.server.specs.schemas import build_request_schema, build_response_schema

from . import BaseUI, Specification, extractors

HTTP_DEFAULT_STATUS = 200
JSONRPC_MEDIATYPE = 'application/json'


def drop_unset(obj: Any) -> Any:
    if isinstance(obj, dict):
        return dict((drop_unset(k), drop_unset(v)) for k, v in obj.items() if k is not UNSET and v is not UNSET)
    if isinstance(obj, (tuple, list, set)):
        return list(drop_unset(v) for v in obj if v is not UNSET)

    return obj


JsonSchema = Dict[str, Any]


@dc.dataclass
class Reference:
    """
    A simple object to allow referencing other components in the OpenAPI document, internally and externally.

    :param ref: the reference identifier.
    :param summary: a short summary which by default SHOULD override that of the referenced component.
    :param description: a description which by default SHOULD override that of the referenced component
    """

    ref: str
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET

    def __post_init__(self) -> None:
        self.__dict__['$ref'] = self.__dict__['ref']
        self.__dataclass_fields__['ref'].name = '$ref'  # noqa


@dc.dataclass
class Contact:
    """
    Contact information for the exposed API.

    :param name: the identifying name of the contact person/organization
    :param url: the URL pointing to the contact information
    :param email: the email address of the contact person/organization
    """

    name: MaybeSet[str] = UNSET
    url: MaybeSet[str] = UNSET
    email: MaybeSet[str] = UNSET


@dc.dataclass
class License:
    """
    License information for the exposed API.

    :param name: the license name used for the API
    :param identifier: an SPDX license expression for the API
    :param url: a URL to the license used for the API
    """

    name: str
    identifier: MaybeSet[str] = UNSET
    url: MaybeSet[str] = UNSET


@dc.dataclass
class Info:
    """
    Metadata about the API.

    :param title: the title of the application
    :param version: the version of the OpenAPI document
    :param summary: a short summary of the API.
    :param description: a description of the application
    :param contact: the contact information for the exposed API
    :param license: the license information for the exposed API
    :param termsOfService: a URL to the Terms of Service for the API
    """

    title: str
    version: str
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    contact: MaybeSet[Contact] = UNSET
    license: MaybeSet[License] = UNSET
    termsOfService: MaybeSet[str] = UNSET


@dc.dataclass
class ServerVariable:
    """
    An object representing a Server Variable for server URL template substitution.

    :param default: the default value to use for substitution, which SHALL be sent if an alternate value is not supplied
    :param enum: an enumeration of string values to be used if the substitution options are from a limited set
    :param description: an optional description for the server variable
    """

    default: str
    enum: MaybeSet[List[str]] = UNSET
    description: MaybeSet[str] = UNSET


@dc.dataclass
class Server:
    """
    Connectivity information of a target server.

    :param url: a URL to the target host
    :param description: an optional string describing the host designated by the URL
    :param variables: a map between a variable name and its value.
                      The value is used for substitution in the server's URL template.
    """

    url: str
    description: MaybeSet[str] = UNSET
    variables: MaybeSet[Dict[str, ServerVariable]] = UNSET


@dc.dataclass
class Link:
    """
    The Link object represents a possible design-time link for a response.

    :param operationRef: a relative or absolute URI reference to an OAS operation
    :param operationId: the name of an existing, resolvable OAS operation, as defined with a unique operationId
    :param parameters: a map representing parameters to pass to an operation as specified with operationId
                       or identified via operationRef
    :param requestBody: a literal value or {expression} to use as a request body when calling the target operation
    :param description: a description of the link
    :param server: a server object to be used by the target operation.
    """

    operationRef: MaybeSet[str] = UNSET
    operationId: MaybeSet[str] = UNSET
    parameters: MaybeSet[Dict[str, Any]] = UNSET
    requestBody: MaybeSet[Any] = UNSET
    description: MaybeSet[str] = UNSET
    server: MaybeSet[Server] = UNSET


@dc.dataclass
class ExternalDocumentation:
    """
    Allows referencing an external resource for extended documentation.

    :param url: a short description of the target documentation.
    :param description: the URL for the target documentation
    """

    url: str
    description: MaybeSet[str] = UNSET


@dc.dataclass
class Tag:
    """
    A list of tags for API documentation control.
    Tags can be used for logical grouping of methods by resources or any other qualifier.

    :param name: the name of the tag
    :param externalDocs: additional external documentation for this tag
    :param description: a short description for the tag
    """

    name: str
    description: MaybeSet[str] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET


class SecuritySchemeType(str, enum.Enum):
    """
    The type of the security scheme.
    """

    APIKEY = 'apiKey'
    HTTP = 'http'
    OAUTH2 = 'oauth2'
    OPENID_CONNECT = 'openIdConnect'


class ApiKeyLocation(str, enum.Enum):
    """
    The location of the API key.
    """

    QUERY = 'query'
    HEADER = 'header'
    COOKIE = 'cookie'


@dc.dataclass
class OAuthFlow:
    """
    Configuration details for a supported OAuth Flow.

    :param authorizationUrl: the authorization URL to be used for this flow
    :param tokenUrl: the token URL to be used for this flow
    :param refreshUrl: the URL to be used for obtaining refresh tokens
    :param scopes: the available scopes for the OAuth2 security scheme
    """

    authorizationUrl: str
    tokenUrl: str
    scopes: Dict[str, str]
    refreshUrl: MaybeSet[str] = UNSET


@dc.dataclass
class OAuthFlows:
    """
    Configuration of the supported OAuth Flows.

    :param implicit: configuration for the OAuth Implicit flow
    :param password: configuration for the OAuth Resource Owner Password flow
    :param clientCredentials: configuration for the OAuth Client Credentials flow
    :param authorizationCode: configuration for the OAuth Authorization Code flow
    """

    implicit: MaybeSet[OAuthFlow] = UNSET
    password: MaybeSet[OAuthFlow] = UNSET
    clientCredentials: MaybeSet[OAuthFlow] = UNSET
    authorizationCode: MaybeSet[OAuthFlow] = UNSET


@dc.dataclass
class SecurityScheme:
    """
    Defines a security scheme that can be used by the operations.

    :param type: the type of the security scheme
    :param name: the name of the header, query or cookie parameter to be used
    :param location: the location of the API key
    :param scheme: the name of the HTTP Authorization scheme to be used in the Authorization header
    :param bearerFormat: a hint to the client to identify how the bearer token is formatted
    :param flows: an object containing configuration information for the flow types supported
    :param openIdConnectUrl:
    :param description: a short description for security scheme
    """

    type: SecuritySchemeType
    scheme: MaybeSet[str] = UNSET
    name: MaybeSet[str] = UNSET
    location: MaybeSet[ApiKeyLocation] = UNSET  # `in` field
    bearerFormat: MaybeSet[str] = UNSET
    flows: MaybeSet[OAuthFlows] = UNSET
    openIdConnectUrl: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET

    def __post_init__(self) -> None:
        # `in` field name is not allowed in python
        self.__dict__['in'] = self.__dict__['location']
        self.__dataclass_fields__['location'].name = 'in'  # noqa


@dc.dataclass
class MethodExample:
    """
    Method usage example.

    :param params: example parameters
    :param result: example result
    :param name: name for the example pairing
    :param summary: short description for the example pairing
    :param description: a verbose explanation of the example pairing
    """

    params: Dict[str, Any]
    result: Any
    version: str = '2.0'
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET


@dc.dataclass
class ExampleObject:
    """
    Method usage example.

    :param value: embedded literal example
    :param summary: short description for the example.
    :param description: long description for the example
    :param externalValue: a URL that points to the literal example
    """

    value: MaybeSet[Any] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    externalValue: MaybeSet[str] = UNSET


@dc.dataclass
class Encoding:
    """
    A single encoding definition applied to a single schema property.

    :param contentType: the Content-Type for encoding a specific property
    :param headers: a map allowing additional information to be provided as headers
    :param style: describes how a specific property value will be serialized depending on its type
    :param explode: when this is true, property values of type array or object generate separate parameters
                    for each value of the array, or key-value-pair of the map
    :param allowReserved: determines whether the parameter value SHOULD allow reserved characters,
                          as defined by RFC3986 to be included without percent-encoding
    """

    contentType: MaybeSet[str] = UNSET
    headers: MaybeSet[Dict[str, Union['Header', Reference]]] = UNSET
    style: MaybeSet[str] = UNSET
    explode: MaybeSet[bool] = UNSET
    allowReserved: MaybeSet[bool] = UNSET


class ParameterLocation(str, enum.Enum):
    """
    The location of the parameter.
    """

    QUERY = 'query'
    HEADER = 'header'
    PATH = 'path'
    COOKIE = 'cookie'


class StyleType(str, enum.Enum):
    """
    Describes how the parameter value will be serialized depending on the type of the parameter value.
    """

    MATRIX = 'matrix'  # path-style parameters defined by RFC6570
    LABEL = 'label'  # label style parameters defined by RFC6570
    FORM = 'form'  # form style parameters defined by RFC6570
    SIMPLE = 'simple'  # simple style parameters defined by RFC6570
    SPACE_DELIMITED = 'spaceDelimited'  # space separated array values
    PIPE_DELIMITED = 'pipeDelimited'  # pipe separated array values
    DEEP_OBJECT = 'deepObject'  # provides a simple way of rendering nested objects using form parameters


@dc.dataclass
class MediaType:
    """
    Each Media Type Object provides schema and examples for the media type identified by its key.

    :param schema: the schema defining the content.
    :param example: example of the media type
    """

    schema: MaybeSet[Dict[str, Any]] = UNSET
    example: MaybeSet[Any] = UNSET
    examples: MaybeSet[Dict[str, ExampleObject]] = UNSET
    encoding: MaybeSet[Dict[str, Encoding]] = UNSET


@dc.dataclass
class RequestBody:
    """
    Describes a single request body.

    :param content: the content of the request body
    :param required: determines if the request body is required in the request
    :param description: a brief description of the request body
    """

    content: Dict[str, MediaType]
    required: MaybeSet[bool] = UNSET
    description: MaybeSet[str] = UNSET


@dc.dataclass
class Parameter:
    """
    Describes a single operation parameter.

    :param name: the name of the parameter
    :param location: the location of the parameter
    :param description: a brief description of the parameter
    :param required: determines whether this parameter is mandatory
    :param deprecated: a parameter is deprecated and SHOULD be transitioned out of usage
    :param allowEmptyValue: the ability to pass empty-valued parameters
    :param style: describes how the parameter value will be serialized depending on the type of the parameter value
    :param explode: when this is true, parameter values of type array or object generate separate parameters
                    for each value of the array or key-value pair of the map
    :param allowReserved: determines whether the parameter value SHOULD allow reserved characters,
                          as defined by RFC3986 :/?#[]@!$&'()*+,;= to be included without percent-encoding
    :param schema: the schema defining the type used for the parameter.
    :param examples: examples of the parameter's potential value
    :param content: a map containing the representations for the parameter
    """

    name: str
    location: ParameterLocation  # `in` field
    description: MaybeSet[str] = UNSET
    required: MaybeSet[bool] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    allowEmptyValue: MaybeSet[bool] = UNSET
    style: MaybeSet[StyleType] = UNSET
    explode: MaybeSet[bool] = UNSET
    allowReserved: MaybeSet[bool] = UNSET
    schema: MaybeSet[JsonSchema] = UNSET
    example: MaybeSet[Any] = UNSET
    examples:  MaybeSet[Dict[str, ExampleObject]] = UNSET
    content: MaybeSet[Dict[str, MediaType]] = UNSET

    def __post_init__(self) -> None:
        # `in` field name is not allowed in python
        self.__dict__['in'] = self.__dict__['location']
        self.__dataclass_fields__['location'].name = 'in'  # noqa


Header = Parameter


@dc.dataclass
class Response:
    """
    A container for the expected responses of an operation.

    :param description: a short description of the response
    :param content: a map containing descriptions of potential response payloads
    """

    description: str
    headers: MaybeSet[Dict[str, Union[Header, Reference]]] = UNSET
    content: MaybeSet[Dict[str, MediaType]] = UNSET
    links: MaybeSet[Dict[str, Union[Link, Reference]]] = UNSET


@dc.dataclass
class Operation:
    """
    Describes a single API operation on a path.

    :param tags: a list of tags for API documentation control
    :param summary: a short summary of what the operation does
    :param description: a verbose explanation of the operation behavior
    :param externalDocs: additional external documentation for this operation
    :param requestBody: the request body applicable for this operation
    :param responses: the list of possible responses as they are returned from executing this operation
    :param deprecated: declares this operation to be deprecated
    :param servers: an alternative server array to service this operation
    :param security: a declaration of which security mechanisms can be used for this operation
    """

    responses: MaybeSet[Dict[str, Union[Response, Reference]]] = UNSET
    requestBody: MaybeSet[Union[RequestBody, Reference]] = UNSET
    tags: MaybeSet[List[str]] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    operationId: MaybeSet[str] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    servers: MaybeSet[List[Server]] = UNSET
    security: MaybeSet[List[Dict[str, List[str]]]] = UNSET
    parameters: MaybeSet[List[Union[Parameter, Reference]]] = UNSET


@dc.dataclass
class Path:
    """
    Describes the interface for the given method name.

    :param summary: an optional, string summary, intended to apply to all operations in this path
    :param description: an optional, string description, intended to apply to all operations in this path
    :param servers: an alternative server array to service all operations in this path
    :param parameters: a list of parameters that are applicable for all the operations described under this path
    """

    get: MaybeSet[Operation] = UNSET
    put: MaybeSet[Operation] = UNSET
    post: MaybeSet[Operation] = UNSET
    delete: MaybeSet[Operation] = UNSET
    options: MaybeSet[Operation] = UNSET
    head: MaybeSet[Operation] = UNSET
    patch: MaybeSet[Operation] = UNSET
    trace: MaybeSet[Operation] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    servers: MaybeSet[List[Server]] = UNSET
    parameters: MaybeSet[Union[Parameter, Reference]] = UNSET


@dc.dataclass
class Components:
    """
    Holds a set of reusable objects for different aspects of the OAS.

    :param securitySchemes: an object to hold reusable Security Scheme Objects
    :param schemas: the definition of input and output data types
    """

    schemas: MaybeSet[Dict[str, JsonSchema]] = UNSET
    responses: MaybeSet[Dict[str, Union[Response, Reference]]] = UNSET
    parameters: MaybeSet[Dict[str, Union[Parameter, Reference]]] = UNSET
    examples: MaybeSet[Dict[str, Union[ExampleObject, Reference]]] = UNSET
    requestBodies: MaybeSet[Dict[str, Union[RequestBody, Reference]]] = UNSET
    headers: MaybeSet[Dict[str, Union[Header, Reference]]] = UNSET
    securitySchemes: MaybeSet[Dict[str, Union[SecurityScheme, Reference]]] = UNSET
    links: MaybeSet[Dict[str, Dict[str, Union[Link, Reference]]]] = UNSET
    pathItems: MaybeSet[Dict[str, Union[Path, Reference]]] = UNSET


@dc.dataclass
class SpecRoot:
    """
    The root object of the OpenAPI description.

    :param info: provides metadata about the API
    :param servers: an array of Server Objects, which provide connectivity information to a target server
    :param externalDocs: additional external documentation
    :param openapi: the semantic version number of the OpenAPI Specification version that the OpenAPI document uses
    :param jsonSchemaDialect: the default value for the $schema keyword within Schema Objects
    :param tags: a list of tags used by the specification with additional metadata
    :param security: a declaration of which security mechanisms can be used across the API
    """

    info: Info
    paths: Dict[str, Path]
    components: Components
    servers: MaybeSet[List[Server]] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    tags: MaybeSet[List[Tag]] = UNSET
    security: MaybeSet[List[Dict[str, List[str]]]] = UNSET
    openapi: str = '3.1.0'
    jsonSchemaDialect: MaybeSet[str] = UNSET


class OpenApiMeta(TypedDict):
    params_schema: MaybeSet[Dict[str, JsonSchema]]
    result_schema: MaybeSet[JsonSchema]
    errors: MaybeSet[List[Type[exceptions.JsonRpcError]]]
    examples: MaybeSet[List[MethodExample]]
    tags: MaybeSet[List[Tag]]
    summary: MaybeSet[str]
    description: MaybeSet[str]
    external_docs: MaybeSet[ExternalDocumentation]
    deprecated: MaybeSet[bool]
    security: MaybeSet[List[Dict[str, List[str]]]]
    parameters: MaybeSet[List[Parameter]]
    servers: MaybeSet[List[Server]]
    component_name_prefix: Optional[str]


def annotate(
    params_schema: MaybeSet[Dict[str, JsonSchema]] = UNSET,
    result_schema: MaybeSet[JsonSchema] = UNSET,
    errors: MaybeSet[List[Type[exceptions.JsonRpcError]]] = UNSET,
    examples: MaybeSet[List[MethodExample]] = UNSET,
    tags: MaybeSet[List[Union[str, Tag]]] = UNSET,
    summary: MaybeSet[str] = UNSET,
    description: MaybeSet[str] = UNSET,
    external_docs: MaybeSet[ExternalDocumentation] = UNSET,
    deprecated: MaybeSet[bool] = UNSET,
    security: MaybeSet[List[Dict[str, List[str]]]] = UNSET,
    parameters: MaybeSet[List[Parameter]] = UNSET,
    servers: MaybeSet[List[Server]] = UNSET,
    component_name_prefix: Optional[str] = None,
) -> Callable[[Func], Func]:
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

    def decorator(method: Func) -> Func:
        meta: OpenApiMeta = dict(
            params_schema=params_schema,
            result_schema=result_schema,
            errors=errors,
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
        )
        utils.set_meta(method, openapi_spec=meta)

        return method

    return decorator


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
    :param schema_extractor: method specification extractor
    :param schema_extractors: method specification extractors. Extractors results will be merged in reverse order
                              (former extractor rewrites the result of the later one)
    :param path: specification url path
    :param security_schemes: an object to hold reusable Security Scheme Objects
    :param ui: web ui instance
    :param ui_path: wet ui path
    """

    def __init__(
        self,
        info: Info,
        path: str = '/openapi.json',
        servers: MaybeSet[List[Server]] = UNSET,
        external_docs: MaybeSet[ExternalDocumentation] = UNSET,
        tags: MaybeSet[List[Tag]] = UNSET,
        security: MaybeSet[List[Dict[str, List[str]]]] = UNSET,
        security_schemes: MaybeSet[Dict[str, Union[SecurityScheme, Reference]]] = UNSET,
        openapi: str = '3.1.0',
        json_schema_dialect: MaybeSet[str] = UNSET,
        schema_extractor: Optional[extractors.BaseSchemaExtractor] = None,
        schema_extractors: Iterable[extractors.BaseSchemaExtractor] = (),
        ui: Optional[BaseUI] = None,
        ui_path: str = '/ui/',
        error_http_status_map: Dict[int, int] = {},
    ):
        super().__init__(path, ui=ui, ui_path=ui_path)

        self._spec = SpecRoot(
            info=info,
            paths={},
            components=Components(securitySchemes=security_schemes),
            servers=servers,
            externalDocs=external_docs,
            tags=tags,
            security=security,
            openapi=openapi,
            jsonSchemaDialect=json_schema_dialect,
        )
        self._error_http_status_map = error_http_status_map
        self._schema_extractors = list(schema_extractors) or [schema_extractor or extractors.BaseSchemaExtractor()]

    def schema(
        self,
        path: str,
        methods_map: Mapping[str, Iterable[Method]] = {},
        component_name_prefix: str = '',
    ) -> Dict[str, Any]:
        spec = copy.deepcopy(self._spec)

        methods_list = [
            (utils.join_path(path, prefix), method)
            for prefix, methods in methods_map.items()
            for method in methods
        ]

        for prefix, method in methods_list:
            method_meta = utils.get_meta(method.method)
            annotated_spec: OpenApiMeta = method_meta.get('openapi_spec', {})

            component_name_prefix = annotated_spec.get('component_name_prefix') or component_name_prefix
            status_errors_map = self._extract_errors(method)
            default_status_errors = status_errors_map.pop(HTTP_DEFAULT_STATUS, [])

            errors_schema = self._extract_errors_schema(spec, method, status_errors_map, component_name_prefix)

            request_schema = self._extract_request_schema(spec, method, component_name_prefix)
            response_schema = self._extract_response_schema(spec, method, default_status_errors, component_name_prefix)

            summary, description = self._extract_description(method)
            tags = self._extract_tags(method)
            servers = self._extract_servers(method)
            parameters = self._extract_parameters(method)
            security = self._extract_security(method)
            deprecated = self._extract_deprecated(method)
            external_docs = self._extract_external_docs(method)

            request_examples, response_success_examples = self._build_examples(
                method, annotated_spec.get('examples', UNSET) or [],
            )

            spec.paths[f'{prefix}#{method.name}'] = Path(
                post=Operation(
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
            )

        return drop_unset(dc.asdict(spec))

    def _extract_errors(self, method: Method) -> Dict[int, List[Type[exceptions.JsonRpcError]]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        errors = annotations.get('errors', UNSET) or []
        for schema_extractor in self._schema_extractors:
            errors.extend(schema_extractor.extract_errors(method.method) or [])

        unique_errors = list({error.code: error for error in errors}.values())
        status_error_map: Dict[int, List[Type[exceptions.JsonRpcError]]] = defaultdict(list)
        for error in unique_errors:
            http_status = self._error_http_status_map.get(error.code, HTTP_DEFAULT_STATUS)
            status_error_map[http_status].append(error)

        return status_error_map

    def _extract_errors_schema(
            self,
            spec: SpecRoot,
            method: Method,
            status_errors_map: Dict[int, List[Type[exceptions.JsonRpcError]]],
            component_name_prefix: str,
    ) -> Dict[int, Dict[str, Any]]:
        status_error_schema_map: Dict[int, Dict[str, Any]] = {}

        for status, errors in status_errors_map.items():
            for schema_extractor in self._schema_extractors:
                if result := schema_extractor.extract_error_response_schema(
                    method.name,
                    method.method,
                    ref_template=f'#/components/schemas/{component_name_prefix}{{model}}',
                    errors=errors,
                ):
                    schema, components = result
                    if components:
                        spec.components.schemas = schemas = spec.components.schemas or {}
                        schemas.update({
                            f"{component_name_prefix}{name}": component
                            for name, component in components.items()
                        })
                    status_error_schema_map[status] = schema
                    break

        return status_error_schema_map

    def _extract_request_schema(
            self,
            spec: SpecRoot,
            method: Method,
            component_name_prefix: str,
    ) -> MaybeSet[Dict[str, Any]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        request_schema: MaybeSet[Dict[str, Any]] = UNSET
        if params_schema := annotations.get('params_schema', UNSET):
            request_schema = build_request_schema(method.name, params_schema)
        else:
            for schema_extractor in self._schema_extractors:
                if result := schema_extractor.extract_request_schema(
                    method.name,
                    method.method,
                    ref_template=f'#/components/schemas/{component_name_prefix}{{model}}',
                    exclude=[method.context] if method.context else [],
                ):
                    request_schema, components = result
                    if components:
                        spec.components.schemas = schemas = spec.components.schemas or {}
                        schemas.update({
                            f"{component_name_prefix}{name}": component
                            for name, component in components.items()
                        })
                    break

        return request_schema

    def _extract_response_schema(
            self,
            spec: SpecRoot,
            method: Method,
            errors: List[Type[exceptions.JsonRpcError]],
            component_name_prefix: str,
    ) -> MaybeSet[Dict[str, Any]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        response_schema: MaybeSet[Dict[str, Any]] = UNSET
        if result_schema := annotations.get('result_schema', UNSET):
            response_schema = build_response_schema(result_schema, errors=errors)
        else:
            for schema_extractor in self._schema_extractors:
                if result := schema_extractor.extract_response_schema(
                    method.name,
                    method.method,
                    ref_template=f'#/components/schemas/{component_name_prefix}{{model}}',
                    errors=errors,
                ):
                    response_schema, components = result
                    if components:
                        spec.components.schemas = schemas = spec.components.schemas or {}
                        schemas.update({
                            f"{component_name_prefix}{name}": component
                            for name, component in components.items()
                        })
                    break

        return response_schema

    def _extract_description(self, method: Method) -> Tuple[MaybeSet[str], MaybeSet[str]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        summary = annotations.get('summary', UNSET)
        description = annotations.get('description', UNSET)

        for schema_extractor in self._schema_extractors:
            if not summary:
                summary = schema_extractor.extract_summary(method.method)
            if not description:
                description = schema_extractor.extract_description(method.method)

        return summary, description

    def _extract_tags(self, method: Method) -> List[Tag]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        tags = annotations.get('tags', UNSET) or []

        return tags

    def _extract_servers(self, method: Method) -> List[Server]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        servers = annotations.get('servers', UNSET) or []

        return servers

    def _extract_parameters(self, method: Method) -> List[Parameter]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        parameters = annotations.get('parameters', UNSET) or []

        return parameters

    def _extract_security(self, method: Method) -> List[Dict[str, List[str]]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        security = annotations.get('security', UNSET) or []

        return security

    def _extract_deprecated(self, method: Method) -> MaybeSet[bool]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        deprecated = annotations.get('deprecated', UNSET)

        for schema_extractor in self._schema_extractors:
            deprecated = deprecated or schema_extractor.extract_deprecation_status(method.method)

        return deprecated

    def _extract_external_docs(self, method: Method) -> MaybeSet[ExternalDocumentation]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenApiMeta = method_meta.get('openapi_spec', {})

        external_docs = annotations.get('external_docs', UNSET)

        return external_docs

    def _build_examples(self, method: Method, examples: List[MethodExample]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        request_examples: Dict[str, Any] = {
            example.summary or f'Example#{i}': ExampleObject(
                summary=example.summary,
                description=example.description,
                value={
                    'jsonrpc': example.version,
                    'id': 1,
                    'method': method.name,
                    'params': example.params,
                },
            ) for i, example in enumerate(examples)
        }

        response_examples: Dict[str, Any] = {
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


class SwaggerUI(BaseUI):
    """
    Swagger UI.

    :param config: documentation configurations
                   (see https://github.com/swagger-api/swagger-ui/blob/master/docs/usage/configuration.md).
    """

    def __init__(self, **configs: Any):
        try:
            import openapi_ui_bundles
        except ImportError:
            raise RuntimeError(
                "openapi-ui-bundles package not found. "
                "Please install pjrpc with extra requirement: pip install pjrpc[openapi-ui-bundles]",
            )

        self._bundle = openapi_ui_bundles
        self._configs = configs

    def get_static_folder(self) -> str:
        return str(self._bundle.swagger_ui.static_path)

    @ft.lru_cache(maxsize=10)
    def get_index_page(self, spec_url: str) -> str:
        index_path = pathlib.Path(self.get_static_folder()) / 'index.html'
        index_page = index_path.read_text()

        config = dict(self._configs, **{'url': spec_url, 'dom_id': '#swagger-ui'})
        config_str = ', '.join(f'{param}: "{value}"' for param, value in config.items())

        return re.sub(
            pattern=r'SwaggerUIBundle\({.*?}\)',
            repl=f'SwaggerUIBundle({{ {config_str} }})',
            string=index_page,
            count=1,
            flags=re.DOTALL,
        )


class RapiDoc(BaseUI):
    """
    RapiDoc UI.

    :param config: documentation configurations (see https://mrin9.github.io/RapiDoc/api.html).
                   Be aware that configuration parameters should be in snake case,
                   for example: parameter `heading-text` should be passed as `heading_text`)
    """

    def __init__(self, **configs: Any):
        try:
            import openapi_ui_bundles.rapidoc
        except ImportError:
            raise RuntimeError(
                "openapi-ui-bundles package not found. "
                "Please install pjrpc with extra requirement: pip install pjrpc[openapi-ui-bundles]",
            )

        self._bundle = openapi_ui_bundles.rapidoc
        self._configs = configs

    def get_static_folder(self) -> str:
        return str(self._bundle.static_path)

    @ft.lru_cache(maxsize=10)
    def get_index_page(self, spec_url: str) -> str:
        index_path = pathlib.Path(self.get_static_folder()) / 'index.html'
        index_page = index_path.read_text()

        config = dict(self._configs, **{'spec_url': spec_url, 'id': 'thedoc'})
        config_str = ' '.join(f'{param.replace("_", "-")}="{value}"' for param, value in config.items())

        return re.sub(
            pattern='<rapi-doc.*?>',
            repl=f'<rapi-doc {config_str}>',
            string=index_page,
            count=1,
            flags=re.DOTALL,
        )


class ReDoc(BaseUI):
    """
    ReDoc UI.

    :param config: documentation configurations (see https://github.com/Redocly/redoc#configuration).
                   Be aware that configuration parameters should be in snake case,
                   for example: parameter `heading-text` should be passed as `heading_text`)
    """

    def __init__(self, **configs: Any):
        try:
            import openapi_ui_bundles.redoc
        except ImportError:
            raise RuntimeError(
                "openapi-ui-bundles package not found. "
                "Please install pjrpc with extra requirement: pip install pjrpc[openapi-ui-bundles]",
            )

        self._bundle = openapi_ui_bundles.redoc
        self._configs = configs

    def get_static_folder(self) -> str:
        return str(self._bundle.static_path)

    @ft.lru_cache(maxsize=10)
    def get_index_page(self, spec_url: str) -> str:
        index_path = pathlib.Path(self.get_static_folder()) / 'index.html'
        index_page = index_path.read_text()

        config = dict(self._configs, **{'spec_url': spec_url})
        config_str = ' '.join(f'{param.replace("_", "-")}="{value}"' for param, value in config.items())

        return re.sub(
            pattern='<redoc.*?>',
            repl=f'<redoc {config_str}>',
            string=index_page,
            count=1,
            flags=re.DOTALL,
        )
