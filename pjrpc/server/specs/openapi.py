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
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Tuple

from pjrpc.common import exceptions
from pjrpc.server import utils, Method

from pjrpc.common import UNSET
from . import extractors
from .extractors import Schema, ErrorExample, Error
from . import BaseUI, Specification


RESULT_SCHEMA = {
    'type': 'object',
    'properties': {
        'jsonrpc': {
            'type': 'string',
            'enum': ['1.0', '2.0'],
        },
        'id': {
            'anyOf': [
                {'type': 'string'},
                {'type': 'number'},
            ],
        },
        'result': {},
    },
    'required': ['jsonrpc', 'id', 'result'],
    'title': 'Success',
    'description': 'JSON-RPC success',
}

ERROR_SCHEMA = {
    'type': 'object',
    'properties': {
        'jsonrpc': {
            'type': 'string',
            'enum': ['1.0', '2.0'],
        },
        'id': {
            'anyOf': [
                {'type': 'string'},
                {'type': 'number'},
            ],
        },
        'error': {
            'type': 'object',
            'properties': {
                'code': {'type': 'integer'},
                'message': {'type': 'string'},
                'data': {'type': 'object'},
            },
            'required': ['code', 'message'],
        },
    },
    'required': ['jsonrpc', 'error'],
    'title': 'Error',
    'description': 'JSON-RPC error',
}

RESPONSE_SCHEMA = {
    'oneOf': [RESULT_SCHEMA, ERROR_SCHEMA],
}

RESULT_SCHEMA_IDX = 0
ERROR_SCHEMA_IDX = 1

REQUEST_SCHEMA = {
    'type': 'object',
    'properties': {
        'jsonrpc': {
            'type': 'string',
            'enum': ['1.0', '2.0'],
        },
        'id': {
            'anyOf': [
                {'type': 'string'},
                {'type': 'number'},
            ],
        },
        'method': {
            'type': 'string',
        },
        'params': {
            'type': 'object',
            'properties': {},
        },
    },
    'required': ['jsonrpc', 'method'],
}

JSONRPC_HTTP_CODE = '200'
JSONRPC_MEDIATYPE = 'application/json'


def drop_unset(obj: Any):
    if isinstance(obj, dict):
        return dict((drop_unset(k), drop_unset(v)) for k, v in obj.items() if k is not UNSET and v is not UNSET)
    if isinstance(obj, (tuple, list, set)):
        return list(drop_unset(v) for v in obj if v is not UNSET)

    return obj


@dc.dataclass(frozen=True)
class Contact:
    """
    Contact information for the exposed API.

    :param name: the identifying name of the contact person/organization
    :param url: the URL pointing to the contact information
    :param email: the email address of the contact person/organization
    """

    name: str = UNSET
    url: str = UNSET
    email: str = UNSET


@dc.dataclass(frozen=True)
class License:
    """
    License information for the exposed API.

    :param name: the license name used for the API
    :param url: a URL to the license used for the API
    """

    name: str
    url: str = UNSET


@dc.dataclass(frozen=True)
class Info:
    """
    Metadata about the API.

    :param title: the title of the application
    :param version: the version of the OpenAPI document
    :param description: a short description of the application
    :param contact: the contact information for the exposed API
    :param license: the license information for the exposed API
    :param termsOfService: a URL to the Terms of Service for the API
    """

    title: str
    version: str
    description: str = UNSET
    contact: Contact = UNSET
    license: License = UNSET
    termsOfService: str = UNSET


@dc.dataclass(frozen=True)
class ServerVariable:
    """
    An object representing a Server Variable for server URL template substitution.

    :param default: the default value to use for substitution, which SHALL be sent if an alternate value is not supplied
    :param enum: an enumeration of string values to be used if the substitution options are from a limited set
    :param description: an optional description for the server variable
    """

    default: str
    enum: List[str] = UNSET
    description: str = UNSET


@dc.dataclass(frozen=True)
class Server:
    """
    Connectivity information of a target server.

    :param url: a URL to the target host
    :param description: an optional string describing the host designated by the URL
    """

    url: str
    description: str = UNSET
    variables: Dict[str, ServerVariable] = UNSET


@dc.dataclass(frozen=True)
class ExternalDocumentation:
    """
    Allows referencing an external resource for extended documentation.

    :param url: a short description of the target documentation.
    :param description: the URL for the target documentation
    """

    url: str
    description: str = UNSET


@dc.dataclass(frozen=True)
class Tag:
    """
    A list of tags for API documentation control.
    Tags can be used for logical grouping of methods by resources or any other qualifier.

    :param name: the name of the tag
    :param externalDocs: additional external documentation for this tag
    :param description: a short description for the tag
    """

    name: str
    description: str = UNSET
    externalDocs: ExternalDocumentation = UNSET


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


@dc.dataclass(frozen=True)
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
    refreshUrl: str = UNSET


@dc.dataclass(frozen=True)
class OAuthFlows:
    """
    Configuration of the supported OAuth Flows.

    :param implicit: configuration for the OAuth Implicit flow
    :param password: configuration for the OAuth Resource Owner Password flow
    :param clientCredentials: configuration for the OAuth Client Credentials flow
    :param authorizationCode: configuration for the OAuth Authorization Code flow
    """

    implicit: OAuthFlow = UNSET
    password: OAuthFlow = UNSET
    clientCredentials: OAuthFlow = UNSET
    authorizationCode: OAuthFlow = UNSET


@dc.dataclass(frozen=True)
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
    scheme: str
    name: str = UNSET
    location: ApiKeyLocation = UNSET  # `in` field
    bearerFormat: str = UNSET
    flows: OAuthFlows = UNSET
    openIdConnectUrl: str = UNSET
    description: str = UNSET

    def __post_init__(self):
        # `in` field name is not allowed in python
        self.__dict__['in'] = self.__dict__['location']
        self.__dataclass_fields__['location'].name = 'in'  # noqa


@dc.dataclass(frozen=False)
class Components:
    """
    Holds a set of reusable objects for different aspects of the OAS.

    :param securitySchemes: an object to hold reusable Security Scheme Objects
    :param schemas: the definition of input and output data types
    """

    securitySchemes: Dict[str, SecurityScheme] = UNSET
    schemas: Dict[str, Dict[str, Any]] = dc.field(default_factory=dict)


@dc.dataclass(frozen=True)
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
    summary: str = UNSET
    description: str = UNSET


@dc.dataclass(frozen=True)
class ExampleObject:
    """
    Method usage example.

    :param value: embedded literal example
    :param summary: short description for the example.
    :param description: long description for the example
    :param externalValue: a URL that points to the literal example
    """

    value: Any
    summary: str = UNSET
    description: str = UNSET
    externalValue: str = UNSET


@dc.dataclass(frozen=True)
class MediaType:
    """
    Each Media Type Object provides schema and examples for the media type identified by its key.

    :param schema: the schema defining the content.
    :param example: example of the media type
    """

    schema: Dict[str, Any]
    examples: Dict[str, ExampleObject] = UNSET


@dc.dataclass(frozen=True)
class Response:
    """
    A container for the expected responses of an operation.

    :param description: a short description of the response
    :param content: a map containing descriptions of potential response payloads
    """

    description: str
    content: Dict[str, MediaType] = UNSET


@dc.dataclass(frozen=True)
class RequestBody:
    """
    Describes a single request body.

    :param content: the content of the request body
    :param required: determines if the request body is required in the request
    :param description: a brief description of the request body
    """

    content: Dict[str, MediaType]
    required: bool = UNSET
    description: str = UNSET


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


@dc.dataclass(frozen=True)
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
    description: str = UNSET
    required: bool = UNSET
    deprecated: bool = UNSET
    allowEmptyValue: bool = UNSET
    style: StyleType = UNSET
    explode: bool = UNSET
    allowReserved: bool = UNSET
    schema: Dict[str, Any] = UNSET
    examples:  Dict[str, ExampleObject] = UNSET
    content: Dict[str, MediaType] = UNSET

    def __post_init__(self):
        # `in` field name is not allowed in python
        self.__dict__['in'] = self.__dict__['location']
        self.__dataclass_fields__['location'].name = 'in'  # noqa


@dc.dataclass(frozen=True)
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

    responses: Dict[str, Response]
    requestBody: RequestBody = UNSET
    tags: List[str] = UNSET
    summary: str = UNSET
    description: str = UNSET
    externalDocs: ExternalDocumentation = UNSET
    deprecated: bool = UNSET
    servers: List[Server] = UNSET
    security: List[Dict[str, List[str]]] = UNSET
    parameters: List[Parameter] = UNSET


@dc.dataclass(frozen=True)
class Path:
    """
    Describes the interface for the given method name.

    :param summary: an optional, string summary, intended to apply to all operations in this path
    :param description: an optional, string description, intended to apply to all operations in this path
    :param servers: an alternative server array to service all operations in this path
    """

    get: Operation = UNSET
    put: Operation = UNSET
    post: Operation = UNSET
    delete: Operation = UNSET
    options: Operation = UNSET
    head: Operation = UNSET
    patch: Operation = UNSET
    trace: Operation = UNSET
    summary: str = UNSET
    description: str = UNSET
    servers: List[Server] = UNSET


def annotate(
    params_schema: Dict[str, Schema] = UNSET,
    result_schema: Schema = UNSET,
    errors_schema: List[Error] = UNSET,
    errors: List[Type[exceptions.JsonRpcError]] = UNSET,
    examples: List[MethodExample] = UNSET,
    error_examples: List[ErrorExample] = UNSET,
    tags: List[str] = UNSET,
    summary: str = UNSET,
    description: str = UNSET,
    external_docs: ExternalDocumentation = UNSET,
    deprecated: bool = UNSET,
    security: List[Dict[str, List[str]]] = UNSET,
    parameters: List[Parameter] = UNSET,
):
    """
    Adds Open Api specification annotation to the method.

    :param params_schema: method parameters JSON schema
    :param result_schema: method result JSON schema
    :param errors_schema: method errors schema
    :param errors: method errors
    :param examples: method usage examples
    :param error_examples: method error examples
    :param tags: a list of tags for method documentation control
    :param summary: a short summary of what the method does
    :param description: a verbose explanation of the method behavior
    :param external_docs: an external resource for extended documentation
    :param deprecated: declares this method to be deprecated
    :param security: a declaration of which security mechanisms can be used for the method
    :param parameters: a list of parameters that are applicable for the method
    """

    def decorator(method: Callable) -> Callable:
        utils.set_meta(
            method,
            openapi_spec=dict(
                params_schema=params_schema,
                result_schema=result_schema,
                errors_schema=errors_schema,
                errors=errors,
                examples=examples,
                error_examples=error_examples,
                tags=[Tag(name=tag) for tag in tags] if tags else UNSET,
                summary=summary,
                description=description,
                external_docs=external_docs,
                deprecated=deprecated,
                security=security,
                parameters=parameters,
            ),
        )

        return method

    return decorator


@dc.dataclass(init=False)
class OpenAPI(Specification):
    """
    OpenAPI Specification.

    :param info: provides metadata about the API
    :param servers: an array of Server Objects, which provide connectivity information to a target server
    :param external_docs: additional external documentation
    :param openapi: the semantic version number of the OpenAPI Specification version that the OpenAPI document uses
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

    info: Info
    paths: Dict[str, Path]
    servers: List[Server] = UNSET
    externalDocs: ExternalDocumentation = UNSET
    tags: List[Tag] = UNSET
    security: List[Dict[str, List[str]]] = UNSET
    components: Components = UNSET
    openapi: str = '3.0.0'

    def __init__(
        self,
        info: Info,
        path: str = '/openapi.json',
        servers: List[Server] = UNSET,
        external_docs: Optional[ExternalDocumentation] = UNSET,
        tags: List[Tag] = UNSET,
        security: List[Dict[str, List[str]]] = UNSET,
        security_schemes: Dict[str, SecurityScheme] = UNSET,
        openapi: str = '3.0.0',
        schema_extractor: Optional[extractors.BaseSchemaExtractor] = None,
        schema_extractors: Iterable[extractors.BaseSchemaExtractor] = (),
        ui: Optional[BaseUI] = None,
        ui_path: str = '/ui/',
    ):
        super().__init__(path, ui=ui, ui_path=ui_path)

        self.info = info
        self.servers = servers
        self.externalDocs = external_docs
        self.tags = tags
        self.security = security
        self.openapi = openapi
        self.paths: Dict[str, Path] = {}
        self.components = Components(securitySchemes=security_schemes)

        self._schema_extractors = list(schema_extractors) or [schema_extractor or extractors.BaseSchemaExtractor()]

    def schema(self, path: str, methods: Iterable[Method] = (), methods_map: Dict[str, Iterable[Method]] = {}) -> dict:
        methods_list: List[Tuple[str, Method]] = []
        methods_list.extend((path, method) for method in methods)
        methods_list.extend(
            (utils.join_path(path, prefix), method)
            for prefix, methods in methods_map.items()
            for method in methods
        )

        for prefix, method in methods_list:
            method_meta = utils.get_meta(method.method)
            annotated_spec = method_meta.get('openapi_spec', {})

            specs: List[Dict[str, Any]] = [
                dict(
                    params_schema=annotated_spec.get('params_schema', UNSET),
                    result_schema=annotated_spec.get('result_schema', UNSET),
                    errors_schema=annotated_spec.get('errors_schema', UNSET),
                    deprecated=annotated_spec.get('deprecated', UNSET),
                    description=annotated_spec.get('description', UNSET),
                    summary=annotated_spec.get('summary', UNSET),
                    tags=annotated_spec.get('tags', UNSET),
                    examples=annotated_spec.get('examples', UNSET),
                    error_examples=annotated_spec.get('error_examples', UNSET),
                    external_docs=annotated_spec.get('external_docs', UNSET),
                    security=annotated_spec.get('security', UNSET),
                    parameters=annotated_spec.get('parameters', UNSET),
                ),
            ]
            for schema_extractor in self._schema_extractors:
                specs.append(
                    dict(
                        params_schema=schema_extractor.extract_params_schema(method.method, exclude=[method.context]),
                        result_schema=schema_extractor.extract_result_schema(method.method),
                        errors_schema=schema_extractor.extract_errors_schema(
                            method.method, annotated_spec.get('errors') or [],
                        ),
                        deprecated=schema_extractor.extract_deprecation_status(method.method),
                        description=schema_extractor.extract_description(method.method),
                        summary=schema_extractor.extract_summary(method.method),
                        tags=schema_extractor.extract_tags(method.method),
                        examples=schema_extractor.extract_examples(method.method),
                        error_examples=schema_extractor.extract_error_examples(
                            method.method, annotated_spec.get('errors') or [],
                        ),
                    ),
                )

            method_spec = self._merge_specs(specs)
            request_schema = self._build_request_schema(method.name, method_spec)
            response_schema = self._build_response_schema(method_spec)

            request_examples = {
                example.summary or f'Example#{i}': ExampleObject(
                    summary=example.summary,
                    description=example.description,
                    value=dict(
                        jsonrpc=example.version,
                        id=1,
                        method=method.name,
                        params=example.params,
                    ),
                ) for i, example in enumerate(method_spec.get('examples') or [])
            }

            response_success_examples = {
                example.summary or f'Example#{i}': ExampleObject(
                    summary=example.summary,
                    description=example.description,
                    value=dict(
                        jsonrpc=example.version,
                        id=1,
                        result=example.result,
                    ),
                ) for i, example in enumerate(method_spec.get('examples') or [])
            }

            response_error_examples = {
                example.message or f'Error#{i}': ExampleObject(
                    summary=example.summary,
                    description=example.description,
                    value=dict(
                        jsonrpc='2.0',
                        id=1,
                        error=dict(
                            code=example.code,
                            message=example.message,
                            data=example.data,
                        ),
                    ),
                ) for i, example in enumerate(
                    utils.unique(
                        [
                            ErrorExample(code=error.code, message=error.message)
                            for error in method_spec.get('errors') or []
                        ],
                        method_spec.get('error_examples') or [],
                        key=lambda item: item.code,
                    ),
                )
            }

            self.paths[f'{prefix}#{method.name}'] = Path(
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
                        JSONRPC_HTTP_CODE: Response(
                            description='JSON-RPC Response',
                            content={
                                JSONRPC_MEDIATYPE: MediaType(
                                    schema=response_schema,
                                    examples={**response_success_examples, **response_error_examples} or UNSET,
                                ),
                            },
                        ),
                    },
                    tags=[tag.name for tag in method_spec.get('tags') or []],
                    summary=method_spec['summary'],
                    description=method_spec['description'],
                    deprecated=method_spec['deprecated'],
                    externalDocs=method_spec.get('external_docs', UNSET),
                    security=method_spec.get('security', UNSET),
                    parameters=method_spec.get('parameters', UNSET),
                ),
            )

        return drop_unset(dc.asdict(self))

    def _merge_specs(self, specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        specs = reversed(specs)
        result = next(specs, {})

        for spec in specs:
            if spec.get('errors_schema', UNSET) is not UNSET:
                schema = {schema.code: schema for schema in result.get('errors_schema') or []}
                schema.update({schema.code: schema for schema in spec['errors_schema']})
                result['errors_schema'] = list(schema.values())

            if spec.get('result_schema', UNSET) is not UNSET:
                if result.get('result_schema', UNSET) is UNSET:
                    result['result_schema'] = spec['result_schema']
                else:
                    cur_schema = result['result_schema']
                    new_schema = spec['result_schema']
                    result['result_schema'] = Schema(
                        new_schema.schema or cur_schema.schema,
                        new_schema.required if new_schema.required is not UNSET else cur_schema.required,
                        new_schema.summary or cur_schema.summary,
                        new_schema.description or cur_schema.description,
                        new_schema.deprecated if new_schema.deprecated is not UNSET else cur_schema.deprecated,
                        new_schema.definitions or cur_schema.definitions,
                    )

            if spec.get('params_schema', UNSET) is not UNSET:
                if result.get('params_schema', UNSET) is UNSET:
                    result['params_schema'] = spec['params_schema']
                else:
                    for param, schema1 in spec['params_schema'].items():
                        schema2 = result['params_schema'].get(param)
                        if schema2 is None:
                            result['params_schema'][param] = schema1
                        else:
                            result['params_schema'][param] = Schema(
                                schema1.schema or schema2.schema,
                                schema1.required if schema1.required is not UNSET else schema2.required,
                                schema1.summary or schema2.summary,
                                schema1.description or schema2.description,
                                schema1.deprecated if schema1.deprecated is not UNSET else schema2.deprecated,
                                schema1.definitions or schema2.definitions,
                            )

            if spec.get('summary', UNSET) is not UNSET:
                result['summary'] = spec['summary']

            if spec.get('description', UNSET) is not UNSET:
                result['description'] = spec['description']

            if spec.get('tags', UNSET) is not UNSET:
                result['tags'] = spec['tags'] + (result.get('tags') or [])

            if spec.get('deprecated', UNSET) is not UNSET:
                result['deprecated'] = spec['deprecated']

            if spec.get('examples', UNSET) is not UNSET:
                result['examples'] = spec['examples'] + (result.get('examples') or [])

            if spec.get('error_examples', UNSET) is not UNSET:
                result['error_examples'] = spec['error_examples'] + (result.get('error_examples') or [])

            if spec.get('external_docs', UNSET) is not UNSET:
                result['external_docs'] = spec['external_docs']

            if spec.get('security', UNSET) is not UNSET:
                result['security'] = spec['security'] + (result.get('security') or [])

            if spec.get('parameters', UNSET) is not UNSET:
                result['parameters'] = spec['parameters'] + (result.get('parameters') or [])

        return result

    def _build_request_schema(self, method_name: str, method_spec: Dict[str, Any]) -> Dict[str, Any]:
        request_schema = copy.deepcopy(REQUEST_SCHEMA)
        request_schema['properties']['method']['enum'] = [method_name]

        for param_name, param_schema in method_spec['params_schema'].items():
            schema = request_schema['properties']['params']['properties'][param_name] = param_schema.schema.copy()
            schema.update({
                'title': param_schema.summary,
                'description': param_schema.description,
                'deprecated': param_schema.deprecated,
            })

            if param_schema.required:
                required_params = request_schema['properties']['params'].setdefault('required', [])
                required_params.append(param_name)

            if param_schema.definitions:
                self.components.schemas.update(param_schema.definitions)

        return request_schema

    def _build_response_schema(self, method_spec: Dict[str, Any]) -> Dict[str, Any]:
        response_schema = copy.deepcopy(RESPONSE_SCHEMA)
        result_schema = method_spec['result_schema']

        response_schema['oneOf'][RESULT_SCHEMA_IDX]['properties']['result'] = result_schema.schema
        if result_schema.definitions:
            self.components.schemas.update(result_schema.definitions)

        if method_spec['errors_schema']:
            errors_schema = []
            response_schema['oneOf'][ERROR_SCHEMA_IDX]['properties']['error'] = {'oneOf': errors_schema}

            for schema in utils.unique(
                [
                    Error(code=error.code, message=error.message)
                    for error in method_spec.get('errors') or []
                ],
                method_spec['errors_schema'],
                key=lambda item: item.code,
            ):
                errors_schema.append({
                    'type': 'object',
                    'properties': {
                        'code': {'type': 'integer', 'enum': [schema.code]},
                        'message': {'type': 'string'},
                        'data': schema.data,
                    },
                    'required': ['code', 'message'] + ['data'] if schema.data_required else [],
                    'deprecated': schema.deprecated,
                    'title': schema.title or schema.message,
                    'description': schema.description,
                })
                if schema.definitions:
                    self.components.schemas.update(schema.definitions)

        return response_schema


class SwaggerUI(BaseUI):
    """
    Swagger UI.

    :param config: documentation configurations
                   (see https://github.com/swagger-api/swagger-ui/blob/master/docs/usage/configuration.md).
    """

    def __init__(self, **configs):
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
        return self._bundle.swagger_ui.static_path

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

    def __init__(self, **configs):
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
        return self._bundle.static_path

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

    def __init__(self, **configs):
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
        return self._bundle.static_path

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
