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
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Union

from pjrpc.common import exceptions
from pjrpc.server import utils, Method

from pjrpc.common import UNSET
from . import extractors
from .extractors import Schema
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
}

RESPONSE_SCHEMA = {
    'oneOf': [RESULT_SCHEMA, ERROR_SCHEMA],
}

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
        'params': {
            'type': 'object',
            'properties': {},
            'required': [],
        },
    },
    'required': ['jsonrpc'],
}

JSONRPC_HTTP_CODE = '200'
JSONRPC_MEDIATYPE = 'application/json'


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
        self.__dict__['in'] = self.__dict__.pop('location')
        field = self.__dataclass_fields__['in'] = self.__dataclass_fields__.pop('location')  # noqa
        field.name = 'in'


@dc.dataclass(frozen=True)
class Components:
    """
    Holds a set of reusable objects for different aspects of the OAS.

    :param securitySchemes: an object to hold reusable Security Scheme Objects
    """

    securitySchemes: Dict[str, SecurityScheme] = UNSET


@dc.dataclass(frozen=True)
class Error:
    """
    Defines an application level error.

    :param code: a Number that indicates the error type that occurred
    :param message: a String providing a short description of the error
    :param data: a Primitive or Structured value that contains additional information about the error
    """

    code: int
    message: str
    data: Dict[str, Any] = UNSET


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
    errors: List[Union[Error, Type[exceptions.JsonRpcError]]] = UNSET,
    examples: List[MethodExample] = UNSET,
    tags: List[str] = UNSET,
    summary: str = UNSET,
    description: str = UNSET,
    external_docs: ExternalDocumentation = UNSET,
    deprecated: bool = UNSET,
    security: List[Dict[str, List[str]]] = UNSET,
):
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
    """

    def decorator(method: Callable) -> Callable:
        utils.set_meta(
            method,
            openapi_spec=dict(
                params_schema=params_schema,
                result_schema=result_schema,
                errors=[
                    error if isinstance(error, Error) else Error(code=error.code, message=error.message)
                    for error in errors
                ] if errors else UNSET,
                examples=examples,
                tags=[Tag(name=tag) for tag in tags] if tags else UNSET,
                summary=summary,
                description=description,
                external_docs=external_docs,
                deprecated=deprecated,
                security=security,
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

        self._schema_extractor = schema_extractor or extractors.BaseSchemaExtractor()

    def schema(self, path: str, methods: Iterable[Method]) -> dict:
        for method in methods:
            path = path.rstrip('/')

            method_meta = utils.get_meta(method.method)
            annotated_spec = method_meta.get('openapi_spec', {})
            extracted_spec: Dict[str, Any] = dict(
                params_schema=self._schema_extractor.extract_params_schema(method.method, exclude=[method.context]),
                result_schema=self._schema_extractor.extract_result_schema(method.method),
                deprecated=self._schema_extractor.extract_deprecation_status(method.method),
                errors=self._schema_extractor.extract_errors_schema(method.method),
                description=self._schema_extractor.extract_description(method.method),
                summary=self._schema_extractor.extract_summary(method.method),
                tags=self._schema_extractor.extract_tags(method.method),
                examples=self._schema_extractor.extract_examples(method.method),
            )
            method_spec = dict(extracted_spec, **{k: v for k, v in annotated_spec.items() if v is not UNSET})

            request_schema = copy.deepcopy(REQUEST_SCHEMA)
            for param_name, param_schema in method_spec['params_schema'].items():
                request_schema['properties']['params']['properties'][param_name] = param_schema.schema
                if param_schema.required:
                    request_schema['properties']['params']['required'].append(param_name)

            response_schema = copy.deepcopy(RESPONSE_SCHEMA)
            response_schema['oneOf'][0]['properties']['result'] = method_spec['result_schema'].schema

            self.paths[f'{path}#{method.name}'] = Path(
                post=Operation(
                    requestBody=RequestBody(
                        description='JSON-RPC Request',
                        content={
                            JSONRPC_MEDIATYPE: MediaType(
                                schema=request_schema,
                                examples={
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
                                } or UNSET,
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
                                    examples={
                                        **{
                                            example.summary or f'Example#{i}': ExampleObject(
                                                summary=example.summary,
                                                description=example.description,
                                                value=dict(
                                                    jsonrpc=example.version,
                                                    id=1,
                                                    result=example.result,
                                                ),
                                            ) for i, example in enumerate(method_spec.get('examples') or [])
                                        },
                                        **{
                                            error.message or f'Error#{i}': ExampleObject(
                                                summary=error.message,
                                                value=dict(
                                                    jsonrpc='2.0',
                                                    id=1,
                                                    error=dict(
                                                        code=error.code,
                                                        message=error.message,
                                                    ),
                                                ),
                                            ) for i, error in enumerate(method_spec.get('errors') or [])
                                        },
                                    } or UNSET,
                                ),
                            },
                        ),
                    },
                    tags=[tag.name for tag in method_spec.get('tags') or []],
                    summary=method_spec.get('summary', UNSET),
                    description=method_spec.get('description', UNSET),
                    externalDocs=method_spec.get('external_docs', UNSET),
                    deprecated=method_spec.get('deprecated', UNSET),
                    security=method_spec.get('security', UNSET),
                ),
            )

        return dc.asdict(
            self,
            dict_factory=lambda iterable: dict(
                filter(lambda item: item[1] is not UNSET, iterable),
            ),
        )


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
