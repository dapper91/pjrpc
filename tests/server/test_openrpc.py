import json

import pydantic

import pjrpc.common.exceptions
import pjrpc.server.specs.extractors.docstring
from pjrpc.server import Method
from pjrpc.server.specs import openrpc as specs
from pjrpc.server.specs import extractors


def test_openapi_schema_generator(resources):
    spec = specs.OpenRPC(
        info=specs.Info(
            version='1.0.0',
            title='Test tittle',
            description='test api',
            contact=specs.Contact(name='owner', email='test@gmal.com'),
            license=specs.License(name='MIT'),
        ),
        external_docs=specs.ExternalDocumentation(url='external-doc.com'),
        servers=[
            specs.Server(
                url='http://test-server',
                name='test server',
                summary='test server summary',
                description='test server description',
            ),
        ],
        schema_extractor=extractors.docstring.DocstringSchemaExtractor(),
    )

    class Model(pydantic.BaseModel):
        field1: str
        field2: int

    class TestError(pjrpc.common.exceptions.JsonRpcError):
        code = 2001
        message = 'test error'

    @specs.annotate(
        errors=[
            TestError,
            specs.Error(code=2002, message='test error'),
        ],
        examples=[
            specs.MethodExample(
                params=[
                    specs.ExampleObject(
                        name='param1',
                        value=1,
                        description='param1 description',
                    ),
                    specs.ExampleObject(
                        name='param2',
                        value={'field1': 'field', 'field2': 2},
                        description='param2 description',
                    ),
                ],
                result=specs.ExampleObject(
                    name='result',
                    value=1,
                    description='result description',
                ),
                summary='example 1 summary',
                description='example 1 description',
            ),
        ],
        tags=['tag1', 'tag2'],
        summary='method1 summary',
        description='method1 description',
        deprecated=True,
    )
    def method1(ctx, param1: int, param2: Model) -> int:
        """
        Method1.

        Description

        :param ctx: context
        :param int param1: param1
        :param dict param2: param2
        :return int: result
        :raises: TestError
        """

    def method2(param1: int, param2) -> Model:
        """
        Method2.

        :param param1: param1
        :type param1: int
        :param param2: param2
        :type param2: dict
        :return dict: result
        """

    @specs.annotate(
        params_schema=[
            specs.ContentDescriptor(
                name='param1',
                schema={},
                summary='param1 summary',
                description='param1 description',
            ),
        ],
        result_schema=specs.ContentDescriptor(
            name='result',
            schema={},
        ),
    )
    def method3(*args, **kwargs):
        pass

    method1 = Method(method1, 'method1', 'ctx')
    method2 = Method(method2, 'method2')
    method3 = Method(method3, 'method3')

    actual_schema = spec.schema('/test/path', methods=[method1, method2, method3])

    assert actual_schema == resources('openrpc-1.json', loader=json.loads)
