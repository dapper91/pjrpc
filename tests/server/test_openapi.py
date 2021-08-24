import json
from typing import Optional

import pydantic

import pjrpc.common.exceptions
import pjrpc.server.specs.extractors.pydantic
from pjrpc.server import Method
from pjrpc.server.specs import openapi as specs
from pjrpc.server.specs import extractors


def test_openapi_schema_generator(resources):
    spec = specs.OpenAPI(
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
                description='test server',
            ),
        ],
        tags=[
            specs.Tag(name='test-tag'),
        ],
        security_schemes=dict(
            basicAuth=specs.SecurityScheme(
                type=specs.SecuritySchemeType.HTTP,
                scheme='basic',
            ),
        ),
        security=[
            dict(basicAuth=[]),
        ],
        schema_extractor=extractors.pydantic.PydanticSchemaExtractor(),
    )

    class SubModel(pydantic.BaseModel):
        field1: str

    class Model(pydantic.BaseModel):
        field1: str
        field2: Optional[int] = 1
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
                params=dict(
                    param1=1,
                    param2={'field1': 'field', 'field2': 2},
                ),
                result=1,
                version='2.0',
                summary='example 1 summary',
                description='example 1 description',
            ),
        ],
        tags=['tag1', 'tag2'],
        summary='method1 summary',
        description='method1 description',
        external_docs=specs.ExternalDocumentation(url='http://doc.info#method1'),
        deprecated=True,
        security=[
            dict(basicAuth=[]),
        ],
    )
    def method1(ctx, param1: int, param2: Model, param3) -> int:
        pass

    def method2(param1: int, param2) -> Model:
        pass

    def method3(param1: Optional[float] = None, param2: int = 1) -> Optional[str]:
        pass

    @specs.annotate(
        params_schema={
            'param1': specs.Schema(
                schema={'type': 'number'},
                summary='param1 summary',
                description='param1 description',
            ),
        },
        result_schema=specs.Schema(
            schema={'type': 'number'},
            summary='result summary',
            description='result description',
        ),
    )
    def method4(param1: int) -> int:
        pass

    def method5(*args, **kwargs) -> None:
        pass

    def method6():
        pass

    method1 = Method(method1, 'method1', 'ctx')
    method2 = Method(method2, 'method2')
    method3 = Method(method3, 'method3')
    method4 = Method(method4, 'method4')
    method5 = Method(method5, 'method5')
    method6 = Method(method6, 'method6')

    actual_schema = spec.schema('/test/path', methods=[method1, method2, method3, method4, method5, method6])

    assert actual_schema == resources('openapi-1.json', loader=json.loads)


def test_ui():
    swagger_ui = specs.SwaggerUI()
    swagger_ui.get_index_page('/path')
    swagger_ui.get_static_folder()

    swagger_ui = specs.ReDoc()
    swagger_ui.get_index_page('/path')
    swagger_ui.get_static_folder()

    swagger_ui = specs.RapiDoc()
    swagger_ui.get_index_page('/path')
    swagger_ui.get_static_folder()
