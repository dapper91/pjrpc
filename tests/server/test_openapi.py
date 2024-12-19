from typing import Any, Dict, Optional

import jsonschema
import pydantic as pd
import pytest
import yaml
from deepdiff.diff import DeepDiff

from pjrpc.common import exceptions
from pjrpc.server.dispatcher import Method
from pjrpc.server.specs import openapi
from pjrpc.server.specs.extractors.docstring import DocstringSchemaExtractor
from pjrpc.server.specs.extractors.pydantic import PydanticSchemaExtractor
from pjrpc.server.specs.openapi import ApiKeyLocation, Contact, ExampleObject, ExternalDocumentation, Info, License
from pjrpc.server.specs.openapi import MethodExample, OpenAPI, Parameter, ParameterLocation, SecurityScheme
from pjrpc.server.specs.openapi import SecuritySchemeType, Server, ServerVariable, StyleType, Tag


def jsonrpc_request_schema(method_name: str, params_schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'title': 'Request',
        'type': 'object',
        'properties': {
            'jsonrpc': {
                'title': 'Version',
                'description': 'JSON-RPC protocol version',
                'type': 'string',
                'enum': ['2.0', '1.0'],
            },
            'id': {
                'title': 'Id',
                'description': 'Request identifier',
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'integer'},
                    {'type': 'null'},
                ],
                'default': None,
                'examples': [1],
            },
            'method': {
                'title': 'Method',
                'description': 'Method name',
                'type': 'string',
                'const': method_name,
            },
            'params': params_schema,
        },
        'required': ['jsonrpc', 'method', 'params'],
        'additionalProperties': False,
    }


def jsonrpc_response_schema(result_schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'title': 'Success',
        'type': 'object',
        'properties': {
            'id': {
                'title': 'Id',
                'description': 'Request identifier',
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'integer'},
                ],
                'examples': [1],
            },
            'jsonrpc': {
                'title': 'Version',
                'description': 'JSON-RPC protocol version',
                'type': 'string',
                'enum': ['2.0', '1.0'],
            },
            'result': result_schema,
        },
        'required': ['jsonrpc', 'id', 'result'],
        'additionalProperties': False,
    }


def jsonrpc_error_schema(title: str, description: str, error_schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'title': title,
        'description': description,
        'type': 'object',
        'properties': {
            'jsonrpc': {
                'description': 'JSON-RPC protocol version',
                'enum': ['1.0', '2.0'],
                'title': 'Version',
                'type': 'string',
            },
            'id': {
                'title': 'Id',
                'description': 'Request identifier',
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'integer'},
                ],
                'examples': [1],
            },
            'error': error_schema,
        },
        'required': ['jsonrpc', 'id', 'error'],
        'additionalProperties': False,
    }


def error_response_component(title: str, description: str, error_schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'title': title,
        'description': description,
        'type': 'object',
        'properties': {
            'jsonrpc': {
                'title': 'Version',
                'description': 'JSON-RPC protocol version',
                'type': 'string',
                'enum': ['1.0', '2.0'],
            },
            'id': {
                'title': 'Id',
                'description': 'Request identifier',
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'integer'},
                ],
                'examples': [1],
            },
            'error': error_schema,
        },
        'required': ['jsonrpc', 'id', 'error'],
        'additionalProperties': False,
    }


def request_body_schema(schema: Dict[str, Any], description: str = 'JSON-RPC Request') -> Dict[str, Any]:
    return {
        'description': description,
        'content': {
            'application/json': {
                'schema': schema,
            },
        },
        'required': True,
    }


def response_schema(schema: Dict[str, Any], description: str = 'JSON-RPC Response') -> Dict[str, Any]:
    return {
        'description': description,
        'content': {
            'application/json': {
                'schema': schema,
            },
        },
    }


def error_component(code: int) -> Dict[str, Any]:
    return {
        'title': 'Error',
        'type': 'object',
        'properties': {
            'code': {
                'title': 'Code',
                'description': 'Error code',
                'type': 'integer',
                'const': code,
            },
            'data': {
                'title': 'Data',
                'description': 'Error additional data',
            },
            'message': {
                'title': 'Message',
                'description': 'Error message',
                'type': 'string',
            },
        },
        'required': ['code', 'message', 'data'],
        'additionalProperties': False,
    }


@pytest.fixture(scope='session')
def oas31_meta(resources):
    return resources('oas-3.1-meta.yaml', loader=yaml.unsafe_load)


def test_info_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            summary='api summary',
            version='1.0',
            description='api description',
            contact=Contact(
                name='contact name',
                url='http://contact.com',
                email='contact@mail.com',
            ),
            license=License(
                name='license name',
                identifier='licence id',
                url='http://license.com',
            ),
            termsOfService='http://term-of-services.com',
        ),
        json_schema_dialect='dialect',
    )

    actual_schema = spec.schema(path='/')
    jsonschema.validate(actual_schema, oas31_meta)

    expected_schema = {
        'openapi': '3.1.0',
        'jsonSchemaDialect': 'dialect',
        'info': {
            'contact': {
                'email': 'contact@mail.com',
                'name': 'contact name',
                'url': 'http://contact.com',
            },
            'description': 'api description',
            'license': {
                'name': 'license name',
                'url': 'http://license.com',
                'identifier': 'licence id',
            },
            'termsOfService': 'http://term-of-services.com',
            'title': 'api title',
            'summary': 'api summary',
            'version': '1.0',
        },
        'paths': {},
        'components': {},
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_servers_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        servers=[
            Server(
                url='http://server.com',
                description='server description',
                variables={
                    'name1': ServerVariable(default='var1', enum=['var1', 'var2'], description='var description'),
                },
            ),
        ],
    )

    actual_schema = spec.schema(path='/')
    jsonschema.validate(actual_schema, oas31_meta)

    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'servers': [{
            'description': 'server description',
            'url': 'http://server.com',
            'variables': {
                'name1': {
                    'default': 'var1',
                    'description': 'var description',
                    'enum': ['var1', 'var2'],
                },
            },
        }],
        'paths': {},
        'components': {},
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_external_docs_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        external_docs=ExternalDocumentation(
            url="http://ex-doc.com",
            description="ext doc description",
        ),
    )

    actual_schema = spec.schema(path='/')
    jsonschema.validate(actual_schema, oas31_meta)

    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'externalDocs': {
            'description': 'ext doc description',
            'url': 'http://ex-doc.com',
        },
        'paths': {},
        'components': {},
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_tags_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        tags=[
            Tag(
                name="tag1",
                description="tag1 description",
                externalDocs=ExternalDocumentation(
                    url="http://tag-ext-doc.com",
                    description="tag ext doc description",
                ),
            ),
        ],
    )

    actual_schema = spec.schema(path='/')
    jsonschema.validate(actual_schema, oas31_meta)

    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'tags': [{
            'description': 'tag1 description',
            'externalDocs': {
                'description': 'tag ext doc description',
                'url': 'http://tag-ext-doc.com',
            },
            'name': 'tag1',
        }],
        'paths': {},
        'components': {},
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_security_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        security=[
            {'jwt': []},
        ],
        security_schemes={
            'basic': SecurityScheme(
                type=SecuritySchemeType.HTTP,
                scheme='basic',
            ),
            'jwt': SecurityScheme(
                type=SecuritySchemeType.HTTP,
                scheme='bearer',
                bearerFormat='JWT',
                description='JWT security schema',
            ),
            'key': SecurityScheme(
                type=SecuritySchemeType.APIKEY,
                name='api-key',
                location=ApiKeyLocation.HEADER,
            ),
        },
    )

    actual_schema = spec.schema(path='/')
    jsonschema.validate(actual_schema, oas31_meta)

    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'security': [{
            'jwt': [],
        }],
        'paths': {},
        'components': {
            'securitySchemes': {
                'basic': {
                    'scheme': 'basic',
                    'type': 'http',
                },
                'jwt': {
                    'bearerFormat': 'JWT',
                    'description': 'JWT security schema',
                    'scheme': 'bearer',
                    'type': 'http',
                },
                'key': {
                    'in': 'header',
                    'name': 'api-key',
                    'type': 'apiKey',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_path_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    def test_method():
        pass

    actual_schema = spec.schema(
        path='/path',
        methods_map={
            '/sub': [Method(test_method)],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/path/sub#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethodParameters',
                    },
                ),
                'TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_multipath_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    def test_method1() -> None:
        pass

    def test_method2() -> int:
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/sub1': [
                Method(test_method1),
            ],
            'sub2': [
                Method(test_method2),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/sub1#test_method1': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'JsonRpcRequest_Literal__test_method1___TestMethod1Parameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethod1Result_',
                            },
                        ),
                    },
                },
            },
            '/sub2#test_method2': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'JsonRpcRequest_Literal__test_method2___TestMethod2Parameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethod2Result_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method1___TestMethod1Parameters_': jsonrpc_request_schema(
                    method_name='test_method1',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethod1Parameters',
                    },
                ),
                'TestMethod1Parameters': {
                    'title': 'TestMethod1Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethod1Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethod1Result',
                    },
                ),
                'TestMethod1Result': {
                    'title': 'TestMethod1Result',
                    'type': 'null',
                },
                'JsonRpcRequest_Literal__test_method2___TestMethod2Parameters_': jsonrpc_request_schema(
                    method_name='test_method2',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethod2Parameters',
                    },
                ),
                'TestMethod2Parameters': {
                    'title': 'TestMethod2Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethod2Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethod2Result',
                    },
                ),
                'TestMethod2Result': {
                    'title': 'TestMethod2Result',
                    'type': 'integer',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_custom_method_name_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    def test_method():
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/sub': [
                Method(test_method, name='custom_method_name'),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/sub#custom_method_name': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'JsonRpcRequest_Literal__custom_method_name___CustomMethodNameParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_CustomMethodNameResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__custom_method_name___CustomMethodNameParameters_': jsonrpc_request_schema(
                    method_name='custom_method_name',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/CustomMethodNameParameters',
                    },
                ),
                'CustomMethodNameParameters': {
                    'title': 'CustomMethodNameParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_CustomMethodNameResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/CustomMethodNameResult',
                    },
                ),
                'CustomMethodNameResult': {
                    'title': 'CustomMethodNameResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_context_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    def test_method(ctx):
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/sub': [
                Method(test_method, context='ctx'),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/sub#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethodParameters',
                    },
                ),
                'TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_request_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
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

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/': [Method(test_method)],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethodParameters',
                    },
                ),
                'TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {
                        'param1': {
                            'title': 'Param1',
                        },
                        'param2': {
                            'title': 'Param2',
                            'type': 'integer',
                        },
                        'param3': {
                            '$ref': '#/components/schemas/Model',
                        },
                        'param4': {
                            'title': 'Param4',
                            'type': 'number',
                            'default': 1.1,
                        },
                        'param5': {
                            'title': 'Param5',
                            'anyOf': [
                                {'type': 'string'},
                                {'type': 'null'},
                            ],
                            'default': None,
                        },
                        'param6': {
                            'title': 'Param6',
                            'description': 'param6 description',
                            'type': 'boolean',
                        },
                    },
                    'required': ['param1', 'param2', 'param3', 'param6'],
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                    'type': 'null',
                },
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


def test_method_response_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
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

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/': [
                Method(test_method1),
                Method(test_method2),
                Method(test_method3),
                Method(test_method4),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/#test_method1': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'JsonRpcRequest_Literal__test_method1___TestMethod1Parameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethod1Result_',
                            },
                        ),
                    },
                },
            },
            '/#test_method2': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'JsonRpcRequest_Literal__test_method2___TestMethod2Parameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethod2Result_',
                            },
                        ),
                    },
                },
            },
            '/#test_method3': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'JsonRpcRequest_Literal__test_method3___TestMethod3Parameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethod3Result_',
                            },
                        ),
                    },
                },
            },
            '/#test_method4': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'JsonRpcRequest_Literal__test_method4___TestMethod4Parameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethod4Result_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method1___TestMethod1Parameters_': jsonrpc_request_schema(
                    method_name='test_method1',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethod1Parameters',
                    },
                ),
                'TestMethod1Parameters': {
                    'title': 'TestMethod1Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethod1Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethod1Result',
                    },
                ),
                'TestMethod1Result': {
                    'title': 'TestMethod1Result',
                    'type': 'null',
                },
                'JsonRpcRequest_Literal__test_method2___TestMethod2Parameters_': jsonrpc_request_schema(
                    method_name='test_method2',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethod2Parameters',
                    },
                ),
                'TestMethod2Parameters': {
                    'title': 'TestMethod2Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethod2Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethod2Result',
                    },
                ),
                'TestMethod2Result': {
                    'title': 'TestMethod2Result',
                    'type': 'integer',
                },
                'JsonRpcRequest_Literal__test_method3___TestMethod3Parameters_': jsonrpc_request_schema(
                    method_name='test_method3',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethod3Parameters',
                    },
                ),
                'TestMethod3Parameters': {
                    'title': 'TestMethod3Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethod3Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethod3Result',
                    },
                ),
                'TestMethod3Result': {
                    'title': 'TestMethod3Result',
                    'anyOf': [
                        {'type': 'string'},
                        {'type': 'null'},
                    ],
                },
                'JsonRpcRequest_Literal__test_method4___TestMethod4Parameters_': jsonrpc_request_schema(
                    method_name='test_method4',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethod4Parameters',
                    },
                ),
                'TestMethod4Parameters': {
                    'title': 'TestMethod4Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethod4Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethod4Result',
                    },
                ),
                'TestMethod4Result': {
                    'title': 'TestMethod4Result',
                    '$ref': '#/components/schemas/Model',
                },
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


def test_method_parameters_annotation_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    @openapi.annotate(
        parameters=[
            Parameter(
                name="param name",
                location=ParameterLocation.HEADER,
                description="param description",
                required=True,
                deprecated=False,
                allowEmptyValue=True,
                style=StyleType.SIMPLE,
                explode=False,
                allowReserved=True,
                schema={'schema key': 'schema value'},
                example="param example",
                examples={
                    'example1': ExampleObject(
                        value="param value",
                        summary="param summary",
                        description="param description",
                    ),
                },
            ),
        ],
    )
    def test_method():
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/path': [
                Method(test_method),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/path#test_method': {
                'post': {
                    'parameters': [
                        {
                            'name': 'param name',
                            'description': 'param description',
                            'in': 'header',
                            'style': 'simple',
                            'example': 'param example',
                            'examples': {
                                'example1': {
                                    'description': 'param description',
                                    'summary': 'param summary',
                                    'value': 'param value',
                                },
                            },
                            'schema': {
                                'schema key': 'schema value',
                            },
                            'explode': False,
                            'allowEmptyValue': True,
                            'allowReserved': True,
                            'deprecated': False,
                            'required': True,
                        },
                    ],
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethodParameters',
                    },
                ),
                'TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_description_annotation_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    @openapi.annotate(
        summary='method summary',
        description='method description',
        tags=['tag1', Tag(name="tag2", description="tag2 description")],
        external_docs=ExternalDocumentation(url="http://ext-doc.com", description="ext doc description"),
        deprecated=True,
        security=[
            {'basic': []},
        ],
        servers=[
            Server(url="http://server.com", description="server description"),
        ],
    )
    def test_method():
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/path': [
                Method(test_method),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/path#test_method': {
                'post': {
                    'summary': 'method summary',
                    'description': 'method description',
                    'tags': ['tag1', 'tag2'],
                    'externalDocs': {
                        'description': 'ext doc description',
                        'url': 'http://ext-doc.com',
                    },
                    'deprecated': True,
                    'security': [{
                        'basic': [],
                    }],
                    'servers': [
                        {'url': 'http://server.com', 'description': 'server description'},
                    ],
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethodParameters',
                    },
                ),
                'TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_examples_annotation_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    @openapi.annotate(
        examples=[
            MethodExample(
                params={"param1": "value1", "param2": 2},
                result="method result",
                summary="example summary",
                description="example description",
            ),
        ],
    )
    def test_method():
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/path': [
                Method(test_method),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/path#test_method': {
                'post': {
                    'requestBody': {
                        'description': 'JSON-RPC Request',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'title': 'Request',
                                    '$ref': '#/components/schemas/'
                                            'JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                                },
                                'examples': {
                                    'example summary': {
                                        'summary': 'example summary',
                                        'description': 'example description',
                                        'value': {
                                            'jsonrpc': '2.0',
                                            'id': 1,
                                            'method': 'test_method',
                                            'params': {
                                                'param1': 'value1',
                                                'param2': 2,
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        'required': True,
                    },
                    'responses': {
                        '200': {
                            'description': 'JSON-RPC Response',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'title': 'Response',
                                        '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_',
                                    },
                                    'examples': {
                                        'example summary': {
                                            'summary': 'example summary',
                                            'description': 'example description',
                                            'value': {
                                                'jsonrpc': '2.0',
                                                'id': 1,
                                                'result': 'method result',
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/TestMethodParameters',
                    },
                ),
                'TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_schema_annotation_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    @openapi.annotate(
        params_schema={
            'param1': {'type': 'string'},
            'param2': {'type': 'number'},
        },
        result_schema={
            'type': 'string',
        },
    )
    def test_method():
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/path': [
                Method(test_method),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'openapi': '3.1.0',
        'paths': {
            '/path#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema=jsonrpc_request_schema(
                            'test_method',
                            params_schema={
                                'title': 'Parameters',
                                'description': 'Reqeust parameters',
                                'type': 'object',
                                'properties': {
                                    'param1': {
                                        'type': 'string',
                                    },
                                    'param2': {
                                        'type': 'number',
                                    },
                                },
                                'additionalProperties': False,
                            },
                        ),
                    ),
                    'responses': {
                        '200': response_schema(
                            schema=jsonrpc_response_schema(
                                result_schema={
                                    'type': 'string',
                                },
                            ),
                        ),
                    },
                },
            },
        },
        'components': {},
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_errors_annotation_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    @openapi.annotate(
        errors=[
            exceptions.MethodNotFoundError,
            exceptions.InvalidParamsError,
        ],
    )
    def test_method():
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/path': [
                Method(test_method),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/path#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            '$ref': '#/components/schemas/JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                            'title': 'Request',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            description='* **-32601** Method not found\n* **-32602** Invalid params',
                            schema={
                                'title': 'Response',
                                'description': '* **-32601** Method not found\n* **-32602** Invalid params',
                                'anyOf': [
                                    {'$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_'},
                                    {'$ref': '#/components/schemas/MethodNotFoundError'},
                                    {'$ref': '#/components/schemas/InvalidParamsError'},
                                ],
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        '$ref': '#/components/schemas/TestMethodParameters',
                        'description': 'Method parameters',
                    },
                ),
                'TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                },
                'MethodNotFoundError': error_response_component(
                    title='MethodNotFoundError',
                    description='**-32601** Method not found',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/JsonRpcError_Literal_-32601__Any_',
                    },
                ),
                'JsonRpcError_Literal_-32601__Any_': error_component(code=-32601),
                'InvalidParamsError': error_response_component(
                    title='InvalidParamsError',
                    description='**-32602** Invalid params',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/JsonRpcError_Literal_-32602__Any_',
                    },
                ),
                'JsonRpcError_Literal_-32602__Any_': error_component(code=-32602),
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_errors_annotation_with_status_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={
            exceptions.MethodNotFoundError.code: 404,
            exceptions.InternalError.code: 500,
            exceptions.ServerError.code: 500,
        },
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    @openapi.annotate(
        errors=[
            exceptions.MethodNotFoundError,
            exceptions.InternalError,
            exceptions.ServerError,
        ],
    )
    def test_method():
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/path': [
                Method(test_method),
            ],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/path#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/JsonRpcRequest_Literal__test_method___TestMethodParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                        '404': response_schema(
                            description='* **-32601** Method not found',
                            schema={
                                '$ref': '#/components/schemas/MethodNotFoundError',
                                'title': 'Response',
                                'description': '* **-32601** Method not found',
                            },
                        ),
                        '500': response_schema(
                            description='* **-32603** Internal error\n* **-32000** Server error',
                            schema={
                                'title': 'Response',
                                'description': '* **-32603** Internal error\n* **-32000** Server error',
                                'anyOf': [
                                    {'$ref': '#/components/schemas/InternalError'},
                                    {'$ref': '#/components/schemas/ServerError'},
                                ],
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'JsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        '$ref': '#/components/schemas/TestMethodParameters',
                        'description': 'Method parameters',
                    },
                ),
                'TestMethodParameters': {
                    'properties': {},
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'additionalProperties': False,
                },
                'JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/TestMethodResult',
                    },
                ),
                'TestMethodResult': {
                    'title': 'TestMethodResult',
                },
                'ServerError': error_response_component(
                    title='ServerError',
                    description='**-32000** Server error',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/JsonRpcError_Literal_-32000__Any_',
                    },
                ),
                'JsonRpcError_Literal_-32000__Any_': error_component(code=-32000),
                'MethodNotFoundError': error_response_component(
                    title='MethodNotFoundError',
                    description='**-32601** Method not found',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/JsonRpcError_Literal_-32601__Any_',
                    },
                ),
                'JsonRpcError_Literal_-32601__Any_': error_component(code=-32601),
                'InternalError': error_response_component(
                    title='InternalError',
                    description='**-32603** Internal error',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/JsonRpcError_Literal_-32603__Any_',
                    },
                ),
                'JsonRpcError_Literal_-32603__Any_': error_component(code=-32603),
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_request_docstring_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractor=DocstringSchemaExtractor(),
    )

    def test_method(
            param1,
            param2: int,
            param3: float = 1.1,
            param4: str = '',
    ) -> int:
        """
        Test method title.
        Test method description.

        :param any param1: Param1 description.
        :param int param2: Param2 description.
        :param float param3: Param3 description.
        :param str param4: Param4 description.
        :return int: Result description.
        """

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/': [Method(test_method)],
        },
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/#test_method': {
                'post': {
                    'summary': 'Test method title.',
                    'description': 'Test method description.',
                    'requestBody': request_body_schema(
                        schema=jsonrpc_request_schema(
                            method_name='test_method',
                            params_schema={
                                'title': 'Parameters',
                                'description': 'Reqeust parameters',
                                'type': 'object',
                                'properties': {
                                    'param1': {
                                        'title': 'Param1',
                                        'description': 'Param1 description.',
                                        'type': 'any',
                                    },
                                    'param2': {
                                        'title': 'Param2',
                                        'description': 'Param2 description.',
                                        'type': 'int',
                                    },
                                    'param3': {
                                        'title': 'Param3',
                                        'description': 'Param3 description.',
                                        'type': 'float',
                                    },
                                    'param4': {
                                        'title': 'Param4',
                                        'description': 'Param4 description.',
                                        'type': 'str',
                                    },
                                },
                                'additionalProperties': False,
                            },
                        ),
                    ),
                    'responses': {
                        '200': response_schema(
                            schema=jsonrpc_response_schema(
                                result_schema={
                                    'title': 'Result',
                                    'description': 'Result description.',
                                    'type': 'int',
                                },
                            ),
                        ),
                    },
                    'deprecated': False,
                },
            },
        },
        'components': {},
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_component_name_prefix(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
        error_http_status_map={},
        schema_extractors=[
            PydanticSchemaExtractor(),
        ],
    )

    class Model1(pd.BaseModel):
        field1: str = pd.Field(title='field1 title')
        field2: str = pd.Field(description='field2 description')

    class Model2(pd.BaseModel):
        field1: str = pd.Field(title='field1 title')
        field2: str = pd.Field(description='field2 description')

    def test_method(param1: Model1) -> Model2:
        pass

    actual_schema = spec.schema(
        path='/',
        methods_map={
            '/': [Method(test_method)],
        },
        component_name_prefix='Prefix',
    )

    jsonschema.validate(actual_schema, oas31_meta)
    expected_schema = {
        'openapi': '3.1.0',
        'info': {
            'title': 'api title',
            'version': '1.0',
        },
        'paths': {
            '/#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'Request',
                            '$ref': '#/components/schemas/'
                                    'PrefixJsonRpcRequest_Literal__test_method___TestMethodParameters_',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'Response',
                                '$ref': '#/components/schemas/PrefixJsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'PrefixJsonRpcRequest_Literal__test_method___TestMethodParameters_': jsonrpc_request_schema(
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/PrefixTestMethodParameters',
                    },
                ),
                'PrefixTestMethodParameters': {
                    'additionalProperties': False,
                    'properties': {
                        'param1': {
                            '$ref': '#/components/schemas/PrefixModel1',
                        },
                    },
                    'required': ['param1'],
                    'title': 'TestMethodParameters',
                    'type': 'object',
                },
                'PrefixJsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/PrefixTestMethodResult',
                    },
                ),
                'PrefixTestMethodResult': {
                    'title': 'TestMethodResult',
                    '$ref': '#/components/schemas/PrefixModel2',
                },
                'PrefixModel1': {
                    'title': 'Model1',
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
                'PrefixModel2': {
                    'title': 'Model2',
                    'type': 'object',
                    'properties': {
                        'field1': {
                            'type': 'string',
                            'title': 'field1 title',
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
