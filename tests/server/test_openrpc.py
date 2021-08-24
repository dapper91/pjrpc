import json
from typing import Optional

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
        external_docs=specs.ExternalDocumentation(url='http://external-doc.com'),
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

    class SubModel(pydantic.BaseModel):
        field1: str

    class Model(pydantic.BaseModel):
        field1: str
        field2: int
        field3: SubModel

    class TestError(pjrpc.common.exceptions.JsonRpcError):
        code = 2001
        message = 'test error 1'

    @specs.annotate(
        errors=[
            TestError,
            specs.Error(code=2002, message='test error 2'),
        ],
        examples=[
            specs.MethodExample(
                name='Simple example',
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
        :param integer param1: param1 summary.
                               description.
        :param object param2: param2 summary.
                              description.
        :return integer: result summary.
                         description.
        :raises TestError: test error
        """

    def method2(param1: int = 1, param2: Optional[float] = None) -> Optional[str]:
        """
        Method2.

        Description.

        :param integer? param1: param1 summary.
        :param number? param2: param2 summary.
        :return string: result summary.
        """

    @specs.annotate(
        params_schema=[
            specs.ContentDescriptor(
                name='param1',
                schema={'type': 'number'},
                summary='param1 summary',
                description='param1 description',
            ),
        ],
        result_schema=specs.ContentDescriptor(
            name='result',
            schema={'type': 'number'},
            summary='result summary',
            description='result description',
        ),
    )
    def method3(param1: int) -> Model:
        pass

    def method4(*args, **kwargs) -> None:
        pass

    def method5():
        pass

    method1 = Method(method1, 'method1', 'ctx')
    method2 = Method(method2, 'method2')
    method3 = Method(method3, 'method3')
    method4 = Method(method4, 'method4')
    method5 = Method(method5, 'method5')

    actual_schema = spec.schema('/test/path', methods=[method1, method2, method3, method4, method5])

    assert actual_schema == resources('openrpc-1.json', loader=json.loads)
