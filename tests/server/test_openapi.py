# flake8: noqa: E501

from typing import Any, Dict, Optional

import jsonschema
import pydantic as pd
import pytest
import yaml
from deepdiff.diff import DeepDiff

from pjrpc.common import exceptions
from pjrpc.server import exclude_positional_param
from pjrpc.server.dispatcher import Method, MethodRegistry
from pjrpc.server.specs import openapi
from pjrpc.server.specs.extractors.pydantic import PydanticMethodInfoExtractor
from pjrpc.server.specs.openapi import ApiKeyLocation, Contact, ExampleObject, ExternalDocumentation, Info, License
from pjrpc.server.specs.openapi import MethodExample, OpenAPI, Parameter, ParameterLocation, SecurityScheme
from pjrpc.server.specs.openapi import SecuritySchemeType, Server, ServerVariable, StyleType, Tag


def jsonrpc_request_schema(title: str, method_name: str, params_schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'title': title,
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
                # identifier='licence id',
                url='http://license.com',
            ),
            termsOfService='http://term-of-services.com',
        ),
        json_schema_dialect='dialect',
    )

    actual_schema = spec.generate(root_endpoint='/', methods={})
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
                # 'identifier': 'licence id',
            },
            'termsOfService': 'http://term-of-services.com',
            'title': 'api title',
            'summary': 'api summary',
            'version': '1.0',
        },
        'paths': {},
        'components': {
            'schemas': {},
        },
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

    actual_schema = spec.generate(root_endpoint='/', methods={})
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
        'components': {
            'schemas': {},
        },
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

    actual_schema = spec.generate(root_endpoint='/', methods={})
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
        'components': {
            'schemas': {},
        },
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

    actual_schema = spec.generate(root_endpoint='/', methods={})
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
        'components': {
            'schemas': {},
        },
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

    actual_schema = spec.generate(root_endpoint='/', methods={})
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
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_path_schema(resources, oas31_meta):
    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    def test_method():
        pass

    test_method = Method(test_method)
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method)

    actual_schema = spec.generate(
        root_endpoint='/path',
        methods={
            '/sub': [
                test_method,
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
            '/path/sub#test_method': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'TestMethodRequest',
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethodResponse',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
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
    )

    def test_method1() -> None:
        pass

    def test_method2() -> int:
        pass

    test_method1 = Method(test_method1)
    test_method2 = Method(test_method2)
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method1)
    generator(test_method2)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/sub1': [
                test_method1,
            ],
            'sub2': [
                test_method2,
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
                            'title': 'TestMethod1Request',
                            '$ref': '#/components/schemas/test_openapi_TestMethod1Request',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethod1Response',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethod1Result_',
                            },
                        ),
                    },
                },
            },
            '/sub2#test_method2': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'TestMethod2Request',
                            '$ref': '#/components/schemas/test_openapi_TestMethod2Request',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethod2Response',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethod2Result_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethod1Request': jsonrpc_request_schema(
                    title='TestMethod1Request',
                    method_name='test_method1',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethod1Parameters',
                    },
                ),
                'test_openapi_TestMethod1Parameters': {
                    'title': 'TestMethod1Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethod1Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethod1Result',
                    },
                ),
                'test_openapi_TestMethod1Result': {
                    'title': 'TestMethod1Result',
                    'type': 'null',
                },
                'test_openapi_TestMethod2Request': jsonrpc_request_schema(
                    title='TestMethod2Request',
                    method_name='test_method2',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethod2Parameters',
                    },
                ),
                'test_openapi_TestMethod2Parameters': {
                    'title': 'TestMethod2Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethod2Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethod2Result',
                    },
                ),
                'test_openapi_TestMethod2Result': {
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
    )

    def test_method():
        pass

    test_method = Method(test_method, name='custom_method_name')
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/sub': [
                test_method,
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
                            'title': 'CustomMethodNameRequest',
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'CustomMethodNameResponse',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='CustomMethodNameRequest',
                    method_name='custom_method_name',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'title': 'CustomMethodNameParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
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
    )

    def test_method(ctx):
        pass

    test_method = Method(test_method)
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor(exclude=exclude_positional_param(0)))
    generator(test_method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/sub': [
                test_method,
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
                            'title': 'TestMethodRequest',
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethodResponse',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
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
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/': [test_method],
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
                            'title': 'TestMethodRequest',
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethodResponse',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
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
                            '$ref': '#/components/schemas/test_openapi_Model',
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
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
                    'title': 'TestMethodResult',
                    'type': 'null',
                },
                'test_openapi_Model': {
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
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(test_method1)
    generator(test_method2)
    generator(test_method3)
    generator(test_method4)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/': [
                test_method1,
                test_method2,
                test_method3,
                test_method4,
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
                            'title': 'TestMethod1Request',
                            '$ref': '#/components/schemas/test_openapi_TestMethod1Request',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethod1Response',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethod1Result_',
                            },
                        ),
                    },
                },
            },
            '/#test_method2': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'TestMethod2Request',
                            '$ref': '#/components/schemas/test_openapi_TestMethod2Request',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethod2Response',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethod2Result_',
                            },
                        ),
                    },
                },
            },
            '/#test_method3': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'TestMethod3Request',
                            '$ref': '#/components/schemas/test_openapi_TestMethod3Request',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethod3Response',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethod3Result_',
                            },
                        ),
                    },
                },
            },
            '/#test_method4': {
                'post': {
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'TestMethod4Request',
                            '$ref': '#/components/schemas/test_openapi_TestMethod4Request',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethod4Response',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethod4Result_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethod1Request': jsonrpc_request_schema(
                    title='TestMethod1Request',
                    method_name='test_method1',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethod1Parameters',
                    },
                ),
                'test_openapi_TestMethod1Parameters': {
                    'title': 'TestMethod1Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethod1Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethod1Result',
                    },
                ),
                'test_openapi_TestMethod1Result': {
                    'title': 'TestMethod1Result',
                    'type': 'null',
                },
                'test_openapi_TestMethod2Request': jsonrpc_request_schema(
                    title='TestMethod2Request',
                    method_name='test_method2',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethod2Parameters',
                    },
                ),
                'test_openapi_TestMethod2Parameters': {
                    'title': 'TestMethod2Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethod2Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethod2Result',
                    },
                ),
                'test_openapi_TestMethod2Result': {
                    'title': 'TestMethod2Result',
                    'type': 'integer',
                },
                'test_openapi_TestMethod3Request': jsonrpc_request_schema(
                    title='TestMethod3Request',
                    method_name='test_method3',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethod3Parameters',
                    },
                ),
                'test_openapi_TestMethod3Parameters': {
                    'title': 'TestMethod3Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethod3Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethod3Result',
                    },
                ),
                'test_openapi_TestMethod3Result': {
                    'title': 'TestMethod3Result',
                    'anyOf': [
                        {'type': 'string'},
                        {'type': 'null'},
                    ],
                },
                'test_openapi_TestMethod4Request': jsonrpc_request_schema(
                    title='TestMethod4Request',
                    method_name='test_method4',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethod4Parameters',
                    },
                ),
                'test_openapi_TestMethod4Parameters': {
                    'title': 'TestMethod4Parameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethod4Result_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethod4Result',
                    },
                ),
                'test_openapi_TestMethod4Result': {
                    'title': 'TestMethod4Result',
                    '$ref': '#/components/schemas/test_openapi_Model',
                },
                'test_openapi_Model': {
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
    registry = MethodRegistry()

    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openapi.metadata(
                parameters=[
                    Parameter(
                        name="param name",
                        location=ParameterLocation.HEADER,
                        description="param description",
                        required=True,
                        deprecated=False,
                        style=StyleType.SIMPLE,
                        explode=False,
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
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/path': [
                method,
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
                            'deprecated': False,
                            'required': True,
                        },
                    ],
                    'requestBody': request_body_schema(
                        schema={
                            'title': 'TestMethodRequest',
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethodResponse',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_description_annotation_schema(resources, oas31_meta):
    registry = MethodRegistry()

    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openapi.metadata(
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
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/path': [
                method,
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
                            'title': 'TestMethodRequest',
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethodResponse',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_examples_annotation_schema(resources, oas31_meta):
    registry = MethodRegistry()

    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openapi.metadata(
                examples=[
                    MethodExample(
                        params={"param1": "value1", "param2": 2},
                        result="method result",
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
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/path': [
                method,
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
                                    'title': 'TestMethodRequest',
                                    '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
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
                                        'title': 'TestMethodResponse',
                                        '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
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
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        'description': 'Method parameters',
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
                    'title': 'TestMethodResult',
                },
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_schema_annotation_schema(resources, oas31_meta):
    registry = MethodRegistry()

    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openapi.metadata(
                params_schema={
                    'param1': {'type': 'string'},
                    'param2': {'type': 'number'},
                },
                result_schema={
                    'type': 'string',
                },
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/path': [
                method,
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
                            title='Request',
                            method_name='test_method',
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
        'components': {
            'schemas': {},
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_errors_annotation_schema(resources, oas31_meta):
    registry = MethodRegistry()

    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openapi.metadata(
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
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/path': [
                method,
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
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                            'title': 'TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            description='* **-32601** Method not found\n* **-32602** Invalid params',
                            schema={
                                'title': 'TestMethodResponse',
                                'description': '* **-32601** Method not found\n* **-32602** Invalid params',
                                'anyOf': [
                                    {'$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_'},
                                    {'$ref': '#/components/schemas/test_openapi_MethodNotFoundError'},
                                    {'$ref': '#/components/schemas/test_openapi_InvalidParamsError'},
                                ],
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                        'description': 'Method parameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'properties': {},
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
                    'title': 'TestMethodResult',
                },
                'test_openapi_MethodNotFoundError': error_response_component(
                    title='MethodNotFoundError',
                    description='**-32601** Method not found',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/test_openapi_JsonRpcError_Literal_-32601__Any_',
                    },
                ),
                'test_openapi_JsonRpcError_Literal_-32601__Any_': error_component(code=-32601),
                'test_openapi_InvalidParamsError': error_response_component(
                    title='InvalidParamsError',
                    description='**-32602** Invalid params',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/test_openapi_JsonRpcError_Literal_-32602__Any_',
                    },
                ),
                'test_openapi_JsonRpcError_Literal_-32602__Any_': error_component(code=-32602),
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_errors_annotation_with_status_schema(resources, oas31_meta):
    registry = MethodRegistry()

    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    @registry.add(
        metadata=[
            openapi.metadata(
                errors=[
                    exceptions.MethodNotFoundError,
                    exceptions.InternalError,
                    exceptions.ServerError,
                ],
            ),
        ],
    )
    def test_method():
        pass

    method = registry.get('test_method')
    generator = openapi.MethodSpecificationGenerator(
        PydanticMethodInfoExtractor(),
        error_http_status_map={
            exceptions.MethodNotFoundError.CODE: 404,
            exceptions.InternalError.CODE: 500,
            exceptions.ServerError.CODE: 500,
        },
    )
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/path': [
                method,
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
                            'title': 'TestMethodRequest',
                            '$ref': '#/components/schemas/test_openapi_TestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethodResponse',
                                '$ref': '#/components/schemas/test_openapi_JsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                        '404': response_schema(
                            description='* **-32601** Method not found',
                            schema={
                                '$ref': '#/components/schemas/test_openapi_MethodNotFoundError',
                                'title': 'TestMethodResponse',
                                'description': '* **-32601** Method not found',
                            },
                        ),
                        '500': response_schema(
                            description='* **-32000** Server error\n* **-32603** Internal error',
                            schema={
                                'title': 'TestMethodResponse',
                                'description': '* **-32000** Server error\n* **-32603** Internal error',
                                'anyOf': [
                                    {'$ref': '#/components/schemas/test_openapi_ServerError'},
                                    {'$ref': '#/components/schemas/test_openapi_InternalError'},
                                ],
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'test_openapi_TestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
                    method_name='test_method',
                    params_schema={
                        '$ref': '#/components/schemas/test_openapi_TestMethodParameters',
                        'description': 'Method parameters',
                    },
                ),
                'test_openapi_TestMethodParameters': {
                    'properties': {},
                    'title': 'TestMethodParameters',
                    'type': 'object',
                    'additionalProperties': False,
                },
                'test_openapi_JsonRpcResponseSuccess_TestMethodResult_': jsonrpc_response_schema(
                    result_schema={
                        'description': 'Method execution result',
                        '$ref': '#/components/schemas/test_openapi_TestMethodResult',
                    },
                ),
                'test_openapi_TestMethodResult': {
                    'title': 'TestMethodResult',
                },
                'test_openapi_ServerError': error_response_component(
                    title='ServerError',
                    description='**-32000** Server error',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/test_openapi_JsonRpcError_Literal_-32000__Any_',
                    },
                ),
                'test_openapi_JsonRpcError_Literal_-32000__Any_': error_component(code=-32000),
                'test_openapi_MethodNotFoundError': error_response_component(
                    title='MethodNotFoundError',
                    description='**-32601** Method not found',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/test_openapi_JsonRpcError_Literal_-32601__Any_',
                    },
                ),
                'test_openapi_JsonRpcError_Literal_-32601__Any_': error_component(code=-32601),
                'test_openapi_InternalError': error_response_component(
                    title='InternalError',
                    description='**-32603** Internal error',
                    error_schema={
                        'description': 'Request error',
                        '$ref': '#/components/schemas/test_openapi_JsonRpcError_Literal_-32603__Any_',
                    },
                ),
                'test_openapi_JsonRpcError_Literal_-32603__Any_': error_component(code=-32603),
            },
        },
    }

    assert not DeepDiff(expected_schema, actual_schema, use_enum_value=True)


def test_method_component_name_prefix(resources, oas31_meta):
    registry = MethodRegistry()

    spec = OpenAPI(
        info=Info(
            title='api title',
            version='1.0',
        ),
    )

    class Model1(pd.BaseModel):
        field1: str = pd.Field(title='field1 title')
        field2: str = pd.Field(description='field2 description')

    class Model2(pd.BaseModel):
        field1: str = pd.Field(title='field1 title')
        field2: str = pd.Field(description='field2 description')

    @registry.add(
        metadata=[
            openapi.metadata(
                component_name_prefix='Prefix',
            ),
        ],
    )
    def test_method(param1: Model1) -> Model2:
        pass

    method = registry.get('test_method')
    generator = openapi.MethodSpecificationGenerator(PydanticMethodInfoExtractor())
    generator(method)

    actual_schema = spec.generate(
        root_endpoint='/',
        methods={
            '/': [method],
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
                            'title': 'TestMethodRequest',
                            '$ref': '#/components/schemas/PrefixTestMethodRequest',
                        },
                    ),
                    'responses': {
                        '200': response_schema(
                            schema={
                                'title': 'TestMethodResponse',
                                '$ref': '#/components/schemas/PrefixJsonRpcResponseSuccess_TestMethodResult_',
                            },
                        ),
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'PrefixTestMethodRequest': jsonrpc_request_schema(
                    title='TestMethodRequest',
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
