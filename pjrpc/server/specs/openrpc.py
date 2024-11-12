"""
OpenRPC specification generator. See https://spec.open-rpc.org/.
"""
import copy
import enum

try:
    import dataclasses as dc
except ImportError:
    raise AssertionError("python 3.7 or later is required")

from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, Type, TypedDict, Union

from pjrpc.common import UNSET, MaybeSet, UnsetType, exceptions
from pjrpc.common.typedefs import Func
from pjrpc.server import Method, utils

from . import Specification, extractors

Json = Union[str, int, float, dict, bool, list, tuple, set, None]  # type: ignore[type-arg]
JsonSchema = Dict[str, Any]


def remove_prefix(s: str, prefix: str) -> str:
    return s[len(prefix):] if s.startswith(prefix) else s


def follow_ref(schema: Dict[str, Any], components: Dict[str, Dict[str, Any]], ref_prefix: str) -> Dict[str, Any]:
    if '$ref' in schema:
        ref = remove_prefix(schema['$ref'], ref_prefix)
        schema = components[ref]

    return schema


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
    enum: MaybeSet[List[str]] = UNSET
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
    variables: MaybeSet[Dict[str, ServerVariable]] = UNSET


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
    params: List[Union[ExampleObject, Reference]]
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
    params: MaybeSet[Any] = UNSET
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
    params: List[Union[ContentDescriptor, Reference]]
    result: Union[ContentDescriptor, Reference]
    errors: MaybeSet[List[Union[Error, Reference]]] = UNSET
    links: MaybeSet[List[Union[Link, Reference]]] = UNSET
    paramStructure: MaybeSet[ParamStructure] = UNSET
    examples: MaybeSet[List[Union[MethodExample, Reference]]] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    tags: MaybeSet[List[Union[Tag, Reference]]] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    servers: MaybeSet[List[Server]] = UNSET


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

    contentDescriptors: MaybeSet[Dict[str, ContentDescriptor]] = UNSET
    schemas: MaybeSet[Dict[str, JsonSchema]] = UNSET
    examples: MaybeSet[Dict[str, ExampleObject]] = UNSET
    links: MaybeSet[Dict[str, Link]] = UNSET
    errors: MaybeSet[Dict[str, Error]] = UNSET
    examplePairingObjects: MaybeSet[Dict[str, MethodExample]] = UNSET
    tags: MaybeSet[Dict[str, Tag]] = UNSET


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
    methods: List[Union[MethodInfo, Reference]] = dc.field(default_factory=list)
    servers: MaybeSet[List[Server]] = UNSET
    externalDocs: MaybeSet[ExternalDocumentation] = UNSET
    openrpc: str = '1.3.2'


class OpenRpcMeta(TypedDict):
    params_schema: MaybeSet[List[ContentDescriptor]]
    result_schema: MaybeSet[ContentDescriptor]
    errors: MaybeSet[List[Error]]
    examples: MaybeSet[List[Union[MethodExample, Reference]]]
    tags: MaybeSet[List[Union[Tag, Reference]]]
    summary: MaybeSet[str]
    description: MaybeSet[str]
    deprecated: MaybeSet[bool]
    external_docs: MaybeSet[ExternalDocumentation]
    servers: MaybeSet[List[Server]]


def annotate(
    params_schema: MaybeSet[List[ContentDescriptor]] = UNSET,
    result_schema: MaybeSet[ContentDescriptor] = UNSET,
    errors: MaybeSet[List[Union[Error, Type[exceptions.JsonRpcError]]]] = UNSET,
    examples: MaybeSet[List[Union[MethodExample, Reference]]] = UNSET,
    summary: MaybeSet[str] = UNSET,
    description: MaybeSet[str] = UNSET,
    tags: MaybeSet[List[Union[Tag, str]]] = UNSET,
    deprecated: MaybeSet[bool] = UNSET,
    external_docs: MaybeSet[ExternalDocumentation] = UNSET,
    servers: MaybeSet[List[Server]] = UNSET,
) -> Callable[[Func], Func]:
    """
    Adds JSON-RPC method to the API specification.

    :param params_schema: a list of parameters that are applicable for this method
    :param result_schema: the description of the result returned by the method
    :param errors: a list of custom application defined errors that MAY be returned
    :param examples: method usage example
    :param summary: a short summary of what the method does
    :param description: a verbose explanation of the method behavior
    :param tags: a list of tags for API documentation control
    :param deprecated: declares this method to be deprecated
    :param external_docs: additional external documentation for the method
    :param servers: an alternative servers array to service this method
    """

    def decorator(method: Func) -> Func:
        meta: OpenRpcMeta = dict(
            params_schema=params_schema,
            result_schema=result_schema,
            errors=[
                error if isinstance(error, Error) else Error(code=error.code, message=error.message)
                for error in errors
            ] if errors else UNSET,
            examples=examples,
            tags=[
                Tag(name=tag) if isinstance(tag, str) else tag
                for tag in tags
            ] if tags else UNSET,
            summary=summary,
            description=description,
            deprecated=deprecated,
            external_docs=external_docs,
            servers=servers,
        )
        utils.set_meta(method, openrpc_spec=meta)

        return method

    return decorator


@dc.dataclass(init=False)
class OpenRPC(Specification):
    """
    OpenRPC Specification.

    :param info: provides metadata about the API
    :param path: specification url path
    :param servers: connectivity information
    :param external_docs: additional external documentation
    :param openrpc: the semantic version number of the OpenRPC Specification version that the OpenRPC document uses
    :param schema_extractor: method specification extractor
    """

    def __init__(
        self,
        info: Info,
        path: str = '/openrpc.json',
        servers: MaybeSet[List[Server]] = UNSET,
        external_docs: MaybeSet[ExternalDocumentation] = UNSET,
        openrpc: str = '1.3.2',
        schema_extractor: Optional[extractors.BaseSchemaExtractor] = None,
    ):
        super().__init__(path)

        self._spec = SpecRoot(
            info=info,
            servers=servers,
            externalDocs=external_docs,
            openrpc=openrpc,
            methods=[],
            components=Components(),
        )
        self._schema_extractor = schema_extractor or extractors.BaseSchemaExtractor()

    def schema(
        self,
        path: str,
        methods_map: Mapping[str, Iterable[Method]] = {},
    ) -> Dict[str, Any]:
        spec = copy.deepcopy(self._spec)

        spec.components.schemas = {}

        for method in methods_map.get('', []):
            summary, description = self._extract_description(method)
            params_schema = self._extract_params_schema(spec, method)
            result_schema = self._extract_result_schema(spec, method)
            errors = self._extract_errors(method)
            deprecated = self._extract_deprecated(method)
            tags = self._extract_tags(method)
            external_docs = self._extract_external_docs(method)
            servers = self._extract_servers(method)
            examples = self._extract_examples(method)

            spec.methods.append(
                MethodInfo(
                    name=method.name,
                    params=list(params_schema),
                    result=result_schema,
                    errors=list(errors) if errors else UNSET,
                    examples=examples or UNSET,
                    summary=summary,
                    description=description,
                    tags=tags or UNSET,
                    deprecated=deprecated,
                    servers=servers or UNSET,
                    externalDocs=external_docs or UNSET,
                ),
            )

        return dc.asdict(
            spec,
            dict_factory=lambda iterable: dict(
                filter(lambda item: not isinstance(item[1], UnsetType), iterable),
            ),
        )

    def _extract_params_schema(self, spec: SpecRoot, method: Method) -> List[ContentDescriptor]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        if not (params_descriptors := annotations.get('params_schema')):
            request_ref_prefix = '#/components/schemas/'
            params_schema, components = self._schema_extractor.extract_params_schema(
                method.name,
                method.method,
                ref_template=f'{request_ref_prefix}{{model}}',
                exclude=[method.context] if method.context else [],
            )
            params_descriptors = [
                ContentDescriptor(
                    name=name,
                    schema=schema,
                    summary=schema.get('title', UNSET),
                    description=schema.get('description', UNSET),
                    required=name in params_schema.get('required', []),
                    deprecated=schema.get('deprecated', UNSET),
                ) for name, schema in params_schema['properties'].items()
            ]

            spec.components.schemas = schemas = spec.components.schemas or {}
            schemas.update(components)

        return params_descriptors

    def _extract_result_schema(self, spec: SpecRoot, method: Method) -> ContentDescriptor:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        if not (result_descriptor := annotations.get('result_schema')):
            response_ref_prefix = '#/components/schemas/'
            result_schema, components = self._schema_extractor.extract_result_schema(
                method.name,
                method.method,
                ref_template=f'{response_ref_prefix}{{model}}',
            )
            result_descriptor = ContentDescriptor(
                name='result',
                schema=result_schema,
                summary=result_schema.get('title', UNSET),
                description=result_schema.get('description', UNSET),
                required='result' in result_schema.get('required', []),
                deprecated=result_schema.get('deprecated', UNSET),
            )
            spec.components.schemas = schemas = spec.components.schemas or {}
            schemas.update(components)

        return result_descriptor

    def _extract_errors(self, method: Method) -> MaybeSet[List[Error]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        errors = annotations.get('errors', UNSET) or []
        errors.extend([
            Error(code=error.code, message=error.message)
            for error in self._schema_extractor.extract_errors(method.method) or []
        ])

        unique_errors = list({error.code: error for error in errors}.values())

        return unique_errors or UNSET

    def _extract_description(self, method: Method) -> Tuple[MaybeSet[str], MaybeSet[str]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        summary = annotations.get('summary', UNSET) or self._schema_extractor.extract_summary(method.method)
        description = annotations.get('description', UNSET) or self._schema_extractor.extract_description(method.method)

        return summary, description

    def _extract_tags(self, method: Method) -> MaybeSet[List[Union[Tag, Reference]]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        tags = annotations.get('tags', UNSET) or []

        return tags or UNSET

    def _extract_servers(self, method: Method) -> MaybeSet[List[Server]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        servers = annotations.get('servers', UNSET) or []

        return servers or UNSET

    def _extract_deprecated(self, method: Method) -> MaybeSet[bool]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        deprecated = annotations.get('deprecated', UNSET)
        if deprecated is UNSET:
            deprecated = self._schema_extractor.extract_deprecation_status(method.method)

        return deprecated

    def _extract_external_docs(self, method: Method) -> MaybeSet[ExternalDocumentation]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        external_docs = annotations.get('external_docs', UNSET)

        return external_docs

    def _extract_examples(self, method: Method) -> MaybeSet[List[Union[MethodExample, Reference]]]:
        method_meta = utils.get_meta(method.method)
        annotations: OpenRpcMeta = method_meta.get('openrpc_spec', {})

        examples = annotations.get('examples', UNSET)

        return examples
