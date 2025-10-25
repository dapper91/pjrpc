"""
OpenRPC specification. See https://spec.open-rpc.org/.
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
    A simple object to allow referencing other components in the specification, internally and externally.
    :param ref: the reference identifier.
    """

    ref: str

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
    :param url: a URL to the license used for the API
    """

    name: str
    url: MaybeSet[str] = UNSET


@dc.dataclass
class Info:
    """
    Metadata about the API.

    :param title: the title of the application
    :param version: the version of the OpenRPC document
    :param description: a verbose description of the application
    :param contact: the contact information for the exposed API
    :param license: the license information for the exposed API
    :param termsOfService: a URL to the Terms of Service for the API
    """

    title: str
    version: str
    description: MaybeSet[str] = UNSET
    contact: MaybeSet[Contact] = UNSET
    license: MaybeSet[License] = UNSET
    termsOfService: MaybeSet[str] = UNSET


@dc.dataclass
class ServerVariable:
    """
    An object representing a Server Variable for server URL template substitution.

    :param default: The default value to use for substitution.
    :param enum: An enumeration of string values to be used if the substitution options are from a limited set.
    :param description: An optional description for the server variable.
    """

    default: str
    enum: MaybeSet[list[str]] = UNSET
    description: MaybeSet[str] = UNSET


@dc.dataclass
class Server:
    """
    Connectivity information of a target server.

    :param name: a name to be used as the canonical name for the server.
    :param url: a URL to the target host. This URL supports Server Variables.
    :param summary: a short summary of what the server is
    :param description: an optional string describing the host designated by the URL
    :param variables: A map between a variable name and its value.
                      The value is passed into the Runtime Expression to produce a server URL.
    """

    name: str
    url: str
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    variables: MaybeSet[dict[str, ServerVariable]] = UNSET


@dc.dataclass
class ExternalDocumentation:
    """
    Allows referencing an external resource for extended documentation.

    :param url: A verbose explanation of the target documentation
    :param description: The URL for the target documentation. Value MUST be in the format of a URL
    """

    url: str
    description: MaybeSet[str] = UNSET


@dc.dataclass
class Tag:
    """
    A list of tags for API documentation control.
    Tags can be used for logical grouping of methods by resources or any other qualifier.

    :param name: the name of the tag
    :param description: a verbose explanation for the tag
    :param externalDocs: additional external documentation for this tag
    """

    name: str
    description: MaybeSet[str] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET


@dc.dataclass
class ExampleObject:
    """
    The ExampleObject object is an object the defines an example.

    :param value: embedded literal example
    :param name: canonical name of the example
    :param summary: short description for the example
    :param description: a verbose explanation of the example
    :param externalValue: a URL that points to the literal example.
    """

    value: Any
    name: str
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    externalValue: MaybeSet[str] = UNSET


@dc.dataclass
class MethodExample:
    """
    The example Pairing object consists of a set of example params and result.

    :param params: example parameters
    :param result: example result
    :param name: name for the example pairing
    :param summary: short description for the example pairing
    :param description: a verbose explanation of the example pairing
    """

    name: str
    params: list[Union[ExampleObject, Reference]]
    result: Union[ExampleObject, Reference]
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET


@dc.dataclass
class ContentDescriptor:
    """
    Content Descriptors are objects that describe content.
    They are reusable ways of describing either parameters or result.

    :param name: name of the content that is being described
    :param schema: schema that describes the content. The Schema Objects MUST follow the specifications outline
                   in the JSON Schema Specification 7 (https://json-schema.org/draft-07/json-schema-release-notes.html)
    :param summary: a short summary of the content that is being described
    :param description: a verbose explanation of the content descriptor behavior
    :param required: determines if the content is a required field
    :param deprecated: specifies that the content is deprecated and SHOULD be transitioned out of usage
    """

    name: str
    schema: JsonSchema
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    required: MaybeSet[bool] = UNSET
    deprecated: MaybeSet[bool] = UNSET


@dc.dataclass
class Error:
    """
    Defines an application level error.

    :param code: a Number that indicates the error type that occurred
    :param message: a String providing a short description of the error
    :param data: a Primitive or Structured value that contains additional information about the error
    """

    code: int
    message: str
    data: MaybeSet[Any] = UNSET


class ParamStructure(str, enum.Enum):
    """
    The expected format of the parameters.
    """

    BY_NAME = 'by-name'
    BY_POSITION = 'by-position'
    EITHER = 'either'


@dc.dataclass
class Link:
    """
    :param name: Canonical name of the link.
    :param description: A description of the link.
    :param summary: Short description for the link.
    :param method: The name of an existing, resolvable OpenRPC method, as defined with a unique method.
    :param params: A map representing parameters to pass to a method as specified with method.
                   The key is the parameter name to be used, whereas the value can be a constant or a runtime
                   expression to be evaluated and passed to the linked method.
    :param server: A server object to be used by the target method.
    """

    name: str
    description: MaybeSet[str] = UNSET
    summary: MaybeSet[str] = UNSET
    method: MaybeSet[str] = UNSET
    params: MaybeSet[dict[str, Any]] = UNSET
    server: MaybeSet[Server] = UNSET


@dc.dataclass
class MethodInfo:
    """
    Describes the interface for the given method name.

    :param name: the canonical name for the method
    :param params: a list of parameters that are applicable for this method
    :param result: the description of the result returned by the method
    :param errors: a list of custom application defined errors that MAY be returned
    :param examples: method usage examples
    :param summary: a short summary of what the method does
    :param description: a verbose explanation of the method behavior
    :param tags: a list of tags for API documentation control
    :param deprecated: declares this method to be deprecated
    :param paramStructure: the expected format of the parameters
    :param externalDocs: additional external documentation for this method
    :param servers: an alternative servers array to service this method
    """

    name: str
    params: list[Union[ContentDescriptor, Reference]]
    result: Union[ContentDescriptor, Reference]
    errors: MaybeSet[list[Union[Error, Reference]]] = UNSET
    links: MaybeSet[list[Union[Link, Reference]]] = UNSET
    paramStructure: MaybeSet[ParamStructure] = UNSET
    examples: MaybeSet[list[Union[MethodExample, Reference]]] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    tags: MaybeSet[list[Union[Tag, Reference]]] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    servers: MaybeSet[list[Server]] = UNSET


@dc.dataclass
class Components:
    """
    Set of reusable objects for different aspects of the OpenRPC.

    :param contentDescriptors: reusable Schema Objects
    :param schemas: reusable Schema Objects
    :param examples: reusable Schema Objects
    :param links: reusable Schema Objects
    :param errors: reusable Schema Objects
    :param examplePairingObjects: reusable Schema Objects
    :param tags: reusable Schema Objects
    """

    contentDescriptors: MaybeSet[dict[str, ContentDescriptor]] = UNSET
    schemas: MaybeSet[dict[str, JsonSchema]] = UNSET
    examples: MaybeSet[dict[str, ExampleObject]] = UNSET
    links: MaybeSet[dict[str, Link]] = UNSET
    errors: MaybeSet[dict[str, Error]] = UNSET
    examplePairingObjects: MaybeSet[dict[str, MethodExample]] = UNSET
    tags: MaybeSet[dict[str, Tag]] = UNSET


@dc.dataclass
class SpecRoot:
    """
    The root object of the OpenRPC document.

    :param info: provides metadata about the API
    :param components: an element to hold various schemas for the specification.
    :param methods: the available methods for the API
    :param servers: connectivity information
    :param externalDocs: additional external documentation
    :param openrpc: the semantic version number of the OpenRPC Specification version that the OpenRPC document uses
    """

    info: Info
    components: Components
    methods: list[Union[MethodInfo, Reference]] = dc.field(default_factory=list)
    servers: MaybeSet[list[Server]] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    openrpc: str = '1.3.2'
