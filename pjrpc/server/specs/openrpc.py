"""
OpenRPC specification generator. See https://spec.open-rpc.org/.
"""
import enum

try:
    import dataclasses as dc
except ImportError:
    raise AssertionError("python 3.7 or later is required")

import itertools as it
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Union

from pjrpc.common import exceptions, UNSET
from pjrpc.server import utils, Method

from . import extractors
from . import Specification

Json = Union[str, int, float, dict, bool, list, tuple, set, None]


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
    :param version: the version of the OpenRPC document
    :param description: a verbose description of the application
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
class Server:
    """
    Connectivity information of a target server.

    :param name: a name to be used as the canonical name for the server.
    :param url: a URL to the target host
    :param summary: a short summary of what the server is
    :param description: an optional string describing the host designated by the URL
    """

    name: str
    url: str
    summary: str = UNSET
    description: str = UNSET


@dc.dataclass(frozen=True)
class ExternalDocumentation:
    """
    Allows referencing an external resource for extended documentation.

    :param url: A verbose explanation of the target documentation
    :param description: The URL for the target documentation. Value MUST be in the format of a URL
    """

    url: str
    description: str = UNSET


@dc.dataclass(frozen=True)
class Tag:
    """
    A list of tags for API documentation control.
    Tags can be used for logical grouping of methods by resources or any other qualifier.

    :param name: the name of the tag
    :param summary: a short summary of the tag
    :param description: a verbose explanation for the tag
    :param externalDocs: additional external documentation for this tag
    """

    name: str
    summary: str = UNSET
    description: str = UNSET
    externalDocs: ExternalDocumentation = UNSET


@dc.dataclass(frozen=True)
class ExampleObject:
    """
    The ExampleObject object is an object the defines an example.

    :param value: embedded literal example
    :param name: canonical name of the example
    :param summary: short description for the example
    :param description: a verbose explanation of the example
    """

    value: Json
    name: str
    summary: str = UNSET
    description: str = UNSET


@dc.dataclass(frozen=True)
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
    params: List[ExampleObject]
    result: ExampleObject
    summary: str = UNSET
    description: str = UNSET


@dc.dataclass(frozen=True)
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
    schema: Dict[str, Any]
    summary: str = UNSET
    description: str = UNSET
    required: bool = UNSET
    deprecated: bool = UNSET


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


class ParamStructure(str, enum.Enum):
    """
    The expected format of the parameters.
    """

    BY_NAME = 'by-name'
    BY_POSITION = 'by-position'
    EITHER = 'either'


@dc.dataclass(frozen=True)
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
    params: List[Union[ContentDescriptor, dict]]
    result: Union[ContentDescriptor, dict]
    errors: List[Error] = UNSET
    paramStructure: ParamStructure = UNSET
    examples: List[MethodExample] = UNSET
    summary: str = UNSET
    description: str = UNSET
    tags: List[Tag] = UNSET
    deprecated: bool = UNSET
    externalDocs: ExternalDocumentation = UNSET
    servers: List[Server] = UNSET


@dc.dataclass(frozen=True)
class Components:
    """
    Set of reusable objects for different aspects of the OpenRPC.

    :param schemas: reusable Schema Objects
    """

    schemas: Dict[str, Any] = dc.field(default_factory=dict)


def annotate(
    params_schema: List[ContentDescriptor] = UNSET,
    result_schema: ContentDescriptor = UNSET,
    errors: List[Union[Error, Type[exceptions.JsonRpcError]]] = UNSET,
    examples: List[MethodExample] = UNSET,
    summary: str = UNSET,
    description: str = UNSET,
    tags: List[Union[Tag, str]] = UNSET,
    deprecated: bool = UNSET,
):
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
    """

    def decorator(method: Callable) -> Callable:
        utils.set_meta(
            method,
            openrpc_spec=dict(
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
            ),
        )

        return method

    return decorator


@dc.dataclass(init=False)
class OpenRPC(Specification):
    """
    OpenRPC Specification.

    :param info: specification information
    :param path: specification url path
    :param servers: connectivity information
    :param external_docs: additional external documentation
    :param openrpc: the semantic version number of the OpenRPC Specification version that the OpenRPC document uses
    :param schema_extractor: method specification extractor
    """

    info: Info
    methods: List[MethodInfo] = dc.field(default_factory=list)
    servers: List[Server] = UNSET
    externalDocs: ExternalDocumentation = UNSET
    openrpc: str = '1.0.0'
    components: Components = UNSET

    def __init__(
        self,
        info: Info,
        path: str = '/openrpc.json',
        servers: List[Server] = UNSET,
        external_docs: Optional[ExternalDocumentation] = UNSET,
        openrpc: str = '1.0.0',
        schema_extractor: Optional[extractors.BaseSchemaExtractor] = None,
    ):
        super().__init__(path)

        self.info = info
        self.servers = servers
        self.externalDocs = external_docs
        self.openrpc = openrpc
        self.methods = []
        self.components = Components()

        self._schema_extractor = schema_extractor

    def schema(self, path: str, methods: Iterable[Method] = (), methods_map: Dict[str, Iterable[Method]] = {}) -> dict:
        for method in it.chain(methods, methods_map.get('', [])):
            method_name = method.name

            method_meta = utils.get_meta(method.method)
            annotated_spec = method_meta.get('openrpc_spec', {})

            params_schema = self._schema_extractor.extract_params_schema(method.method, exclude=[method.context])
            result_schema = self._schema_extractor.extract_result_schema(method.method)
            extracted_spec = dict(
                params_schema=[
                    ContentDescriptor(
                        name=name,
                        schema=schema.schema,
                        summary=schema.summary,
                        description=schema.description,
                        required=schema.required,
                        deprecated=schema.deprecated,
                    ) for name, schema in params_schema.items()
                ],
                result_schema=ContentDescriptor(
                    name='result',
                    schema=result_schema.schema,
                    summary=result_schema.summary,
                    description=result_schema.description,
                    required=result_schema.required,
                    deprecated=result_schema.deprecated,
                ),
                errors=self._schema_extractor.extract_errors_schema(method.method),
                deprecated=self._schema_extractor.extract_deprecation_status(method.method),
                description=self._schema_extractor.extract_description(method.method),
                summary=self._schema_extractor.extract_summary(method.method),
                tags=self._schema_extractor.extract_tags(method.method),
                examples=[
                    MethodExample(
                        name=example.summary,
                        params=[
                            ExampleObject(
                                value=param_value,
                                name=param_name,
                            )
                            for param_name, param_value in example.params.items()
                        ],
                        result=ExampleObject(
                            name='result',
                            value=example.result,
                        ),
                        summary=example.summary,
                        description=example.description,
                    )
                    for example in self._schema_extractor.extract_examples(method.method) or []
                ],
            )
            method_spec = extracted_spec.copy()
            method_spec.update((k, v) for k, v in annotated_spec.items() if v is not UNSET)

            self.methods.append(
                MethodInfo(
                    name=method_name,
                    params=method_spec['params_schema'],
                    result=method_spec['result_schema'],
                    errors=method_spec['errors'],
                    examples=method_spec['examples'],
                    summary=method_spec['summary'],
                    description=method_spec['description'],
                    tags=method_spec['tags'],
                    deprecated=method_spec['deprecated'],
                ),
            )

            for param_schema in params_schema.values():
                if param_schema.definitions:
                    self.components.schemas.update(param_schema.definitions)

            if result_schema.definitions:
                self.components.schemas.update(result_schema.definitions)

        return dc.asdict(
            self,
            dict_factory=lambda iterable: dict(
                filter(lambda item: item[1] is not UNSET, iterable),
            ),
        )
