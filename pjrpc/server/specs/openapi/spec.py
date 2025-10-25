"""
OpenAPI Specification. See https://swagger.io/specification/.
"""

import dataclasses as dc
import enum
from typing import Any, Union

from pjrpc.common import UNSET, MaybeSet

Json = Union[str, int, float, dict[str, 'Json'], bool, list['Json'], tuple['Json'], set['Json'], None]
JsonSchema = dict[str, Json]


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
    enum: MaybeSet[list[str]] = UNSET
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
    variables: MaybeSet[dict[str, ServerVariable]] = UNSET


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
    parameters: MaybeSet[dict[str, Any]] = UNSET
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
    scopes: dict[str, str]
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
    :param summary: short description for the example pairing
    :param description: a verbose explanation of the example pairing
    """

    params: dict[str, Any]
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
    headers: MaybeSet[dict[str, Union['Header', Reference]]] = UNSET
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

    schema: MaybeSet[dict[str, Any]] = UNSET
    example: MaybeSet[Any] = UNSET
    examples: MaybeSet[dict[str, ExampleObject]] = UNSET
    encoding: MaybeSet[dict[str, Encoding]] = UNSET


@dc.dataclass
class RequestBody:
    """
    Describes a single request body.

    :param content: the content of the request body
    :param required: determines if the request body is required in the request
    :param description: a brief description of the request body
    """

    content: dict[str, MediaType]
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
    examples:  MaybeSet[dict[str, ExampleObject]] = UNSET
    content: MaybeSet[dict[str, MediaType]] = UNSET

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
    headers: MaybeSet[dict[str, Union[Header, Reference]]] = UNSET
    content: MaybeSet[dict[str, MediaType]] = UNSET
    links: MaybeSet[dict[str, Union[Link, Reference]]] = UNSET


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

    responses: MaybeSet[dict[str, Union[Response, Reference]]] = UNSET
    requestBody: MaybeSet[Union[RequestBody, Reference]] = UNSET
    tags: MaybeSet[list[str]] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    operationId: MaybeSet[str] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    servers: MaybeSet[list[Server]] = UNSET
    security: MaybeSet[list[dict[str, list[str]]]] = UNSET
    parameters: MaybeSet[list[Union[Parameter, Reference]]] = UNSET


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
    servers: MaybeSet[list[Server]] = UNSET
    parameters: MaybeSet[Union[Parameter, Reference]] = UNSET


@dc.dataclass
class Components:
    """
    Holds a set of reusable objects for different aspects of the OAS.

    :param securitySchemes: an object to hold reusable Security Scheme Objects
    :param schemas: the definition of input and output data types
    """

    schemas: MaybeSet[dict[str, JsonSchema]] = UNSET
    responses: MaybeSet[dict[str, Union[Response, Reference]]] = UNSET
    parameters: MaybeSet[dict[str, Union[Parameter, Reference]]] = UNSET
    examples: MaybeSet[dict[str, Union[ExampleObject, Reference]]] = UNSET
    requestBodies: MaybeSet[dict[str, Union[RequestBody, Reference]]] = UNSET
    headers: MaybeSet[dict[str, Union[Header, Reference]]] = UNSET
    securitySchemes: MaybeSet[dict[str, Union[SecurityScheme, Reference]]] = UNSET
    links: MaybeSet[dict[str, dict[str, Union[Link, Reference]]]] = UNSET
    pathItems: MaybeSet[dict[str, Union[Path, Reference]]] = UNSET


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
    paths: dict[str, Path]
    components: Components
    servers: MaybeSet[list[Server]] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    tags: MaybeSet[list[Tag]] = UNSET
    security: MaybeSet[list[dict[str, list[str]]]] = UNSET
    openapi: str = '3.1.0'
    jsonSchemaDialect: MaybeSet[str] = UNSET
