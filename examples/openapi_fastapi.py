import uuid
from typing import Annotated, Any, Mapping

import fastapi
import pydantic as pd

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import fastapi as integration
from pjrpc.server.specs import extractors, openapi
from pjrpc.server.specs.openapi import ui
from pjrpc.server.validators import pydantic as validators

methods = pjrpc.server.MethodRegistry(
    validator_factory=validators.PydanticValidatorFactory(exclude=integration.is_fastapi_request),
    metadata_processors=[
        openapi.MethodSpecificationGenerator(
            extractor=extractors.pydantic.PydanticMethodInfoExtractor(
                exclude=integration.is_fastapi_request,
            ),
        ),
    ],
)

credentials = {"admin": "admin"}


UserName = Annotated[
    str,
    pd.Field(description="User name", examples=["John"]),
]

UserSurname = Annotated[
    str,
    pd.Field(description="User surname", examples=["Doe"]),
]

UserAge = Annotated[
    int,
    pd.Field(description="User age", examples=[25]),
]

UserId = Annotated[
    uuid.UUID,
    pd.Field(description="User identifier", examples=["08b02cf9-8e07-4d06-b569-2c24309c1dc1"]),
]


class UserIn(pd.BaseModel, title="User data"):
    """
    User registration data.
    """

    name: UserName
    surname: UserSurname
    age: UserAge


class UserOut(UserIn, title="User data"):
    """
    Registered user data.
    """

    id: UserId


class AlreadyExistsError(pjrpc.server.exceptions.TypedError):
    """
    User already registered error.
    """

    CODE = 2001
    MESSAGE = "user already exists"


class NotFoundError(pjrpc.server.exceptions.TypedError):
    """
    User not found error.
    """

    CODE = 2002
    MESSAGE = "user not found"


@methods.add(
    pass_context='request',
    metadata=[
        openapi.metadata(
            summary="Creates a user",
            tags=['users'],
            errors=[AlreadyExistsError],
        ),
    ],
)
def add_user(request: fastapi.Request[Mapping[str, Any]], user: UserIn) -> UserOut:
    """
    Creates a user.

    :param request: http request
    :param object user: user data
    :return object: registered user
    :raise AlreadyExistsError: user already exists
    """


@methods.add(
    pass_context='request',
    metadata=[
        openapi.metadata(
            summary="Returns a user",
            tags=['users'],
            errors=[NotFoundError],
        ),
    ],
)
def get_user(request: fastapi.Request[Mapping[str, Any]], user_id: UserId) -> UserOut:
    """
    Returns a user.

    :param request: http request
    :param object user_id: user id
    :return object: registered user
    :raise NotFoundError: user not found
    """


@methods.add(
    pass_context='request',
    metadata=[
        openapi.metadata(
            summary="Deletes a user",
            tags=['users'],
            errors=[NotFoundError],
            deprecated=True,
        ),
    ],
)
def delete_user(request: fastapi.Request[Mapping[str, Any]], user_id: UserId) -> None:
    """
    Deletes a user.

    :param request: http request
    :param object user_id: user id
    :raise NotFoundError: user not found
    """


class JSONEncoder(pjrpc.server.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, pd.BaseModel):
            return o.model_dump()
        if isinstance(o, uuid.UUID):
            return str(o)

        return super().default(o)


openapi_spec = openapi.OpenAPI(
    info=openapi.Info(version="1.0.0", title="User storage"),
)

jsonrpc_app = integration.Application('/api/v1')
jsonrpc_app.add_methods(methods)

jsonrpc_app.add_spec(openapi_spec, path='openapi.json')
jsonrpc_app.add_spec_ui('swagger', ui.SwaggerUI(), spec_url='../openapi.json')
jsonrpc_app.add_spec_ui('redoc', ui.ReDoc(), spec_url='../openapi.json')


app = fastapi.FastAPI()
app.mount("/rpc", jsonrpc_app.http_app)
