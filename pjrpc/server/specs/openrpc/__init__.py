"""
OpenRPC specification generator. See https://spec.open-rpc.org/.
"""

import dataclasses as dc
from typing import Any, Callable, Iterable, Mapping, Union

from pjrpc.common import UNSET, MaybeSet, UnsetType, exceptions
from pjrpc.server.dispatcher import Method
from pjrpc.server.specs import Specification
from pjrpc.server.specs.extractors import BaseMethodInfoExtractor

from .spec import Components, Contact, ContentDescriptor, Error, ExampleObject, ExternalDocumentation, Info, Json
from .spec import JsonSchema, License, Link, MethodExample, MethodInfo, ParamStructure, Reference, Server
from .spec import ServerVariable, SpecRoot, Tag

__all__ = [
    'Components',
    'Contact',
    'ContentDescriptor',
    'Error',
    'ExampleObject',
    'ExternalDocumentation',
    'Info',
    'Json',
    'JsonSchema',
    'License',
    'Link',
    'metadata',
    'MethodExample',
    'MethodInfo',
    'MethodMetadata',
    'OpenRPC',
    'ParamStructure',
    'Reference',
    'Server',
    'ServerVariable',
    'SpecRoot',
    'Tag',
]

MethodType = Callable[..., Any]


class OpenRPC(Specification):
    """
    OpenRPC Specification.

    :param info: provides metadata about the API
    :param servers: connectivity information
    :param external_docs: additional external documentation
    :param openrpc: the semantic version number of the OpenRPC Specification version that the OpenRPC document uses
    """

    def __init__(
        self,
        info: Info,
        servers: MaybeSet[list[Server]] = UNSET,
        external_docs: MaybeSet[ExternalDocumentation] = UNSET,
        openrpc: str = '1.3.2',
    ):
        self._info = info
        self._servers = servers
        self._external_docs = external_docs
        self._openrpc = openrpc

    def generate(self, root_endpoint: str, methods: Mapping[str, Iterable[Method]]) -> dict[str, Any]:
        spec_root = SpecRoot(
            info=self._info,
            servers=self._servers,
            externalDocs=self._external_docs,
            openrpc=self._openrpc,
            methods=[],
            components=Components(),
        )
        spec_root.components.schemas = {}

        for method in methods.get('', []):
            for meta in method.metadata:
                if isinstance(meta, MethodSpecification):
                    spec_root.methods.append(meta.method_info)
                    spec_root.components.schemas.update(meta.component_schemas or {})

        return dc.asdict(
            spec_root,
            dict_factory=lambda iterable: dict(
                filter(lambda item: not isinstance(item[1], UnsetType), iterable),
            ),
        )


@dc.dataclass(frozen=True)
class MethodMetadata:
    params_schema: MaybeSet[list[ContentDescriptor]] = UNSET
    result_schema: MaybeSet[ContentDescriptor] = UNSET
    errors: MaybeSet[list[Error]] = UNSET
    examples: MaybeSet[list[Union[MethodExample, Reference]]] = UNSET
    tags: MaybeSet[list[Union[Tag, Reference]]] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    external_docs: MaybeSet[ExternalDocumentation] = UNSET
    servers: MaybeSet[list[Server]] = UNSET

    def merge(self, other: 'MethodMetadata') -> 'MethodMetadata':
        return MethodMetadata(
            params_schema=self.params_schema if self.params_schema is not UNSET else other.params_schema,
            result_schema=self.result_schema if self.result_schema is not UNSET else other.result_schema,
            summary=self.summary if self.summary is not UNSET else other.summary,
            description=self.description if self.description is not UNSET else other.description,
            deprecated=self.deprecated if self.deprecated is not UNSET else other.deprecated,
            external_docs=self.external_docs if self.external_docs is not UNSET else other.external_docs,
            errors=((self.errors or []) + (other.errors or [])) or UNSET,
            examples=((self.examples or []) + (other.examples or [])) or UNSET,
            tags=((self.tags or []) + (other.tags or [])) or UNSET,
            servers=((self.servers or []) + (other.servers or [])) or UNSET,
        )


def metadata(
    params_schema: MaybeSet[list[ContentDescriptor]] = UNSET,
    result_schema: MaybeSet[ContentDescriptor] = UNSET,
    errors: MaybeSet[list[Union[Error, type[exceptions.TypedError]]]] = UNSET,
    examples: MaybeSet[list[Union[MethodExample, Reference]]] = UNSET,
    summary: MaybeSet[str] = UNSET,
    description: MaybeSet[str] = UNSET,
    tags: MaybeSet[list[Union[Tag, str]]] = UNSET,
    deprecated: MaybeSet[bool] = UNSET,
    external_docs: MaybeSet[ExternalDocumentation] = UNSET,
    servers: MaybeSet[list[Server]] = UNSET,
) -> MethodMetadata:
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

    return MethodMetadata(
        params_schema=params_schema,
        result_schema=result_schema,
        errors=[
            error if isinstance(error, Error) else Error(code=error.CODE, message=error.MESSAGE)
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


@dc.dataclass(frozen=True)
class MethodSpecification:
    method_info: MethodInfo
    component_schemas: MaybeSet[dict[str, JsonSchema]] = UNSET


class MethodSpecificationGenerator:
    def __init__(self, extractor: BaseMethodInfoExtractor):
        self._extractor = extractor

    def __call__(self, method: Method) -> Method:
        method_metadata = MethodMetadata()
        for meta in method.metadata:
            if isinstance(meta, MethodMetadata):
                method_metadata = method_metadata.merge(meta)

        method_specification = self._generate(method.func, method.name, method_metadata)
        method.metadata.append(method_specification)

        return method

    def _generate(self, method: MethodType, method_name: str, method_metadata: MethodMetadata) -> MethodSpecification:
        tags = method_metadata.tags
        examples = method_metadata.examples
        servers = method_metadata.servers
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

        component_schemas: dict[str, JsonSchema] = {}
        params_schema, params_component_schemas = self._extract_params_schema(method, method_name, method_metadata)
        component_schemas.update(params_component_schemas)

        result_schema, result_component_schemas = self._extract_result_schema(method, method_name, method_metadata)
        component_schemas.update(result_component_schemas)

        errors = self._extract_errors(method, method_metadata)

        method_info = MethodInfo(
            name=method_name,
            params=list(params_schema),
            result=result_schema,
            errors=list(errors) if errors else UNSET,
            examples=examples,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            externalDocs=external_docs,
            servers=servers,
        )

        return MethodSpecification(method_info, component_schemas)

    def _extract_params_schema(
        self,
        method: MethodType,
        method_name: str,
        method_metadata: MethodMetadata,
    ) -> tuple[list[ContentDescriptor], dict[str, JsonSchema]]:
        component_schemas: dict[str, JsonSchema] = {}
        if not (params_descriptors := method_metadata.params_schema):
            request_ref_prefix = '#/components/schemas/'
            params_schema, component_schemas = self._extractor.extract_params_schema(
                method_name,
                method,
                ref_template=f'{request_ref_prefix}{{model}}',
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

        return params_descriptors, component_schemas

    def _extract_result_schema(
        self,
        method: MethodType,
        method_name: str,
        method_metadata: MethodMetadata,
    ) -> tuple[ContentDescriptor, dict[str, JsonSchema]]:
        component_schemas: dict[str, JsonSchema] = {}
        if not (result_descriptor := method_metadata.result_schema):
            response_ref_prefix = '#/components/schemas/'
            result_schema, component_schemas = self._extractor.extract_result_schema(
                method_name,
                method,
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

        return result_descriptor, component_schemas

    def _extract_errors(self, method: MethodType, method_metadata: MethodMetadata) -> MaybeSet[list[Error]]:
        errors = method_metadata.errors or []
        errors.extend([
            Error(code=error.CODE, message=error.MESSAGE)
            for error in self._extractor.extract_errors(method) or []
        ])

        unique_errors = list({error.code: error for error in errors}.values())

        return unique_errors or UNSET
