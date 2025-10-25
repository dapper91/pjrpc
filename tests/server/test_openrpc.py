import json
from typing import Optional

import jsonschema
import pydantic as pd
import pytest
from deepdiff.diff import DeepDiff

from pjrpc.common import exceptions
from pjrpc.server import MethodRegistry
from pjrpc.server.dispatcher import Method
from pjrpc.server.specs import openrpc
from pjrpc.server.specs.extractors.pydantic import PydanticMethodInfoExtractor
from pjrpc.server.specs.openrpc import Contact, ContentDescriptor, ExampleObject, ExternalDocumentation, Info, License
from pjrpc.server.specs.openrpc import MethodExample, OpenRPC, Server, ServerVariable, Tag
from pjrpc.server.utils import exclude_positional_param


@pytest.fixture(scope='session')
def openrpc13_meta(resources):
    return resources('openrpc-1.3.2.json', loader=json.loads)


def test_info_schema(resources, openrpc13_meta):
    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
            description='api description',
            contact=Contact(
                name='contact name',
                url='http://contact.com',
                email='contact@mail.com',
            ),
            license=License(
                name='license name',
                url='http://license.com',
            ),
            termsOfService='http://term-of-services.com',
        ),
    )

    actual_schema = spec.generate(root_endpoint='/', methods={})
    jsonschema.validate(actual_schema, openrpc13_meta)

    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'version': '1.0',
            'title': 'api title',
            'description': 'api description',
            'contact': {
                'name': 'contact name',
                'url': 'http://contact.com',
                'email': 'contact@mail.com',
            },
            'license': {
                'name': 'license name',
                'url': 'http://license.com',
            },
            'termsOfService': 'http://term-of-services.com',
        },
        'methods': [],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_servers_schema(resources, openrpc13_meta):
    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
        servers=[
            Server(
                name='server name',
                url='http://server.com',
                summary='server summary',
                description='server description',
                variables={
                    'name1': ServerVariable(default='var1', enum=['var1', 'var2'], description='var description'),
                },
            ),
        ],
    )

    actual_schema = spec.generate(root_endpoint='/', methods={})
    jsonschema.validate(actual_schema, openrpc13_meta)

    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [],
        'servers': [
            {
                'name': 'server name',
                'summary': 'server summary',
                'description': 'server description',
                'url': 'http://server.com',
                'variables': {
                    'name1': {
                        'default': 'var1',
                        'enum': ['var1', 'var2'],
                        'description': 'var description',
                    },
                },
            },
        ],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_external_docs_schema(resources, openrpc13_meta):
    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
        external_docs=ExternalDocumentation(
            url="http://ex-doc.com",
            description="ext doc description",
        ),
    )

    actual_schema = spec.generate(root_endpoint='/', methods={})
    jsonschema.validate(actual_schema, openrpc13_meta)

    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'version': '1.0',
            'title': 'api title',
        },
        'methods': [],
        'externalDocs': {
            'url': 'http://ex-doc.com',
            'description': 'ext doc description',
        },
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_custom_method_name_schema(resources, openrpc13_meta):
    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    def test_method():
        pass

    test_method = Method(test_method, name='custom_method_name')
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                test_method,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'custom_method_name',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'CustomMethodNameResult',
                    'schema': {
                        'title': 'CustomMethodNameResult',
                    },
                    'required': False,
                },
            },
        ],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_context_schema(resources, openrpc13_meta):
    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    def test_method(ctx):
        pass

    test_method = Method(test_method)
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor(exclude=exclude_positional_param(0)))
    generator(test_method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                test_method,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'test_method',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethodResult',
                    'schema': {
                        'title': 'TestMethodResult',
                    },
                    'required': False,
                },
            },
        ],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_request_schema(resources, openrpc13_meta):
    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    class Model(pd.BaseModel):
        field1: str = pd.Field(title='field1 title')
        field2: str = pd.Field(description='field2 description')

    def test_method(
            param1,
            param2: int,
            param3: Model,
            param4: float = 1.1,
            param5: Optional[str] = None,
            param6: bool = pd.Field(description="param6 description"),
    ) -> None:
        pass

    test_method = Method(test_method)
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                test_method,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'test_method',
                'params': [
                    {
                        'name': 'param1',
                        'summary': 'Param1',
                        'schema': {
                            'title': 'Param1',
                        },
                        'required': True,
                    },
                    {
                        'name': 'param2',
                        'summary': 'Param2',
                        'schema': {
                            'title': 'Param2',
                            'type': 'integer',
                        },
                        'required': True,
                    },
                    {
                        'name': 'param3',
                        'schema': {
                            '$ref': '#/components/schemas/Model',
                        },
                        'required': True,
                    },
                    {
                        'name': 'param4',
                        'summary': 'Param4',
                        'schema': {
                            'title': 'Param4',
                            'type': 'number',
                            'default': 1.1,
                        },
                        'required': False,
                    },
                    {
                        'name': 'param5',
                        'summary': 'Param5',
                        'schema': {
                            'title': 'Param5',
                            'anyOf': [
                                {'type': 'string'},
                                {'type': 'null'},
                            ],
                            'default': None,
                        },
                        'required': False,
                    },
                    {
                        'name': 'param6',
                        'summary': 'Param6',
                        'description': 'param6 description',
                        'schema': {
                            'title': 'Param6',
                            'description': 'param6 description',
                            'type': 'boolean',
                        },
                        'required': True,
                    },
                ],
                'result': {
                    'name': 'result',
                    'schema': {
                        'title': 'TestMethodResult',
                        'type': 'null',
                    },
                    'summary': 'TestMethodResult',
                    'required': False,
                },
            },
        ],
        'components': {
            'schemas': {
                'Model': {
                    'title': 'Model',
                    'type': 'object',
                    'properties': {
                        'field1': {
                            'title': 'field1 title',
                            'type': 'string',
                        },
                        'field2': {
                            'title': 'Field2',
                            'description': 'field2 description',
                            'type': 'string',
                        },
                    },
                    'required': ['field1', 'field2'],
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_response_schema(resources, openrpc13_meta):
    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    class Model(pd.BaseModel):
        field1: str = pd.Field(title='field1 title')
        field2: str = pd.Field(description='field2 description')

    def test_method1() -> None:
        pass

    def test_method2() -> int:
        pass

    def test_method3() -> Optional[str]:
        pass

    def test_method4() -> Model:
        pass

    test_method1 = Method(test_method1)
    test_method2 = Method(test_method2)
    test_method3 = Method(test_method3)
    test_method4 = Method(test_method4)
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method1)
    generator(test_method2)
    generator(test_method3)
    generator(test_method4)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                test_method1,
                test_method2,
                test_method3,
                test_method4,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'test_method1',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethod1Result',
                    'schema': {
                        'title': 'TestMethod1Result',
                        'type': 'null',
                    },
                    'required': False,
                },
            },
            {
                'name': 'test_method2',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethod2Result',
                    'schema': {
                        'title': 'TestMethod2Result',
                        'type': 'integer',
                    },
                    'required': False,
                },
            },
            {
                'name': 'test_method3',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethod3Result',
                    'schema': {
                        'title': 'TestMethod3Result',
                        'anyOf': [
                            {'type': 'string'},
                            {'type': 'null'},
                        ],
                    },
                    'required': False,
                },
            },
            {
                'name': 'test_method4',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethod4Result',
                    'schema': {
                        'title': 'TestMethod4Result',
                        '$ref': '#/components/schemas/Model',
                    },
                    'required': False,
                },
            },
        ],
        'components': {
            'schemas': {
                'Model': {
                    'title': 'Model',
                    'type': 'object',
                    'properties': {
                        'field1': {
                            'title': 'field1 title',
                            'type': 'string',
                        },
                        'field2': {
                            'title': 'Field2',
                            'description': 'field2 description',
                            'type': 'string',
                        },
                    },
                    'required': ['field1', 'field2'],
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_description_annotation_schema(resources, openrpc13_meta):
    registry = MethodRegistry()

    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openrpc.metadata(
                summary='method summary',
                description='method description',
                tags=[
                    'tag1',
                    Tag(
                        name="tag2",
                        description="tag2 description",
                        externalDocs=ExternalDocumentation(
                            url="http://tag-ext-doc.com",
                            description="tag doc description",
                        ),
                    ),
                ],
                external_docs=ExternalDocumentation(
                    url="http://ext-doc.com",
                    description="ext doc description",
                ),
                deprecated=True,
                servers=[
                    Server(
                        name="server name",
                        summary="server summary",
                        description="server description",
                        url="http://server.com",
                        variables={
                            'name1': ServerVariable(
                                default='var1',
                                enum=['var1', 'var2'],
                                description='var description',
                            ),
                        },
                    ),
                ],
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                method,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'test_method',
                'summary': 'method summary',
                'description': 'method description',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethodResult',
                    'schema': {
                        'title': 'TestMethodResult',
                    },
                    'required': False,
                },
                'tags': [
                    {
                        'name': 'tag1',
                    },
                    {
                        'name': 'tag2',
                        'description': 'tag2 description',
                        'externalDocs': {
                            'description': 'tag doc description',
                            'url': 'http://tag-ext-doc.com',
                        },
                    },
                ],
                'deprecated': True,
                'externalDocs': {
                    'description': 'ext doc description',
                    'url': 'http://ext-doc.com',
                },
                'servers': [
                    {
                        'name': 'server name',
                        'summary': 'server summary',
                        'description': 'server description',
                        'url': 'http://server.com',
                        'variables': {
                            'name1': {
                                'description': 'var description',
                                'default': 'var1',
                                'enum': ['var1', 'var2'],
                            },
                        },
                    },
                ],
            },
        ],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_examples_annotation_schema(resources, openrpc13_meta):
    registry = MethodRegistry()

    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openrpc.metadata(
                examples=[
                    MethodExample(
                        name='example name',
                        params=[
                            ExampleObject(
                                value={"param1": "value1", "param2": 2},
                                name="param name",
                                summary="param summary",
                                description="param description",
                                externalValue="http://param.com",
                            ),
                        ],
                        result=ExampleObject(
                            value="method result",
                            name="result name",
                            summary="result summary",
                            description="result description",
                            externalValue="http://result.com",
                        ),
                        summary="example summary",
                        description="example description",
                    ),
                ],
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                method,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'test_method',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethodResult',
                    'schema': {
                        'title': 'TestMethodResult',
                    },
                    'required': False,
                },
                'examples': [
                    {
                        'name': 'example name',
                        'summary': 'example summary',
                        'description': 'example description',
                        'params': [
                            {
                                'name': 'param name',
                                'summary': 'param summary',
                                'description': 'param description',
                                'value': {
                                    'param1': 'value1',
                                    'param2': 2,
                                },
                                'externalValue': 'http://param.com',
                            },
                        ],
                        'result': {
                            'name': 'result name',
                            'summary': 'result summary',
                            'description': 'result description',
                            'value': 'method result',
                            'externalValue': 'http://result.com',
                        },
                    },
                ],
            },
        ],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_schema_annotation_schema(resources, openrpc13_meta):
    registry = MethodRegistry()

    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openrpc.metadata(
                params_schema=[
                    ContentDescriptor(
                        name="params name",
                        schema={
                            'param1': {'type': 'string'},
                            'param2': {'type': 'number'},
                        },
                        summary="params summary",
                        description="params description",
                        required=True,
                        deprecated=True,
                    ),
                ],
                result_schema=ContentDescriptor(
                    name="result name",
                    schema={'type': 'string'},
                    summary="result summary",
                    description="result description",
                    required=True,
                    deprecated=True,
                ),
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                method,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'test_method',
                'params': [
                    {
                        'name': 'params name',
                        'summary': 'params summary',
                        'description': 'params description',
                        'schema': {
                            'param1': {
                                'type': 'string',
                            },
                            'param2': {
                                'type': 'number',
                            },
                        },
                        'required': True,
                        'deprecated': True,
                    },
                ],
                'result': {
                    'name': 'result name',
                    'summary': 'result summary',
                    'description': 'result description',
                    'schema': {
                        'type': 'string',
                    },
                    'required': True,
                    'deprecated': True,
                },
            },
        ],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_errors_annotation_schema(resources, openrpc13_meta):
    registry = MethodRegistry()

    spec = OpenRPC(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openrpc.metadata(
                errors=[
                    exceptions.MethodNotFoundError,
                    exceptions.InvalidParamsError,
                ],
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openrpc.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '': [
                method,
            ],
        },
    )

    jsonschema.validate(actual_schema, openrpc13_meta)
    expected_schema = {
        'openrpc': '1.3.2',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'methods': [
            {
                'name': 'test_method',
                'params': [],
                'result': {
                    'name': 'result',
                    'summary': 'TestMethodResult',
                    'schema': {
                        'title': 'TestMethodResult',
                    },
                    'required': False,
                },
                'errors': [
                    {
                        'code': -32601,
                        'message': 'Method not found',
                    },
                    {
                        'code': -32602,
                        'message': 'Invalid params',
                    },
                ],
            },
        ],
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)
