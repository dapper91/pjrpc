import uuid
from collections import defaultdict

import pydantic
from django.http.request import HttpRequest

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.validators import pydantic as validators
from pjrpc.server.specs import openapi as specs

methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()
db = defaultdict(dict)


class UserIn(pydantic.BaseModel):
    """
    User registration data.
    """

    name: str
    surname: str
    age: int


class UserOut(UserIn):
    """
    Registered user data.
    """

    id: uuid.UUID


class AlreadyExistsError(pjrpc.exc.JsonRpcError):
    """
    User already registered error.
    """

    code = 2001
    message = "user already exists"


class NotFoundError(pjrpc.exc.JsonRpcError):
    """
    User not found error.
    """

    code = 2002
    message = "user not found"


@specs.annotate(
    tags=['users'],
    errors=[AlreadyExistsError],
    examples=[
        specs.MethodExample(
            summary="Simple example",
            params=dict(
                user={
                    'name': 'John',
                    'surname': 'Doe',
                    'age': 25,
                },
            ),
            result={
                'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                'name': 'John',
                'surname': 'Doe',
                'age': 25,
            },
        ),
    ],
)
@methods.add(context='request')
@validator.validate
def add_user(request: HttpRequest, user: UserIn) -> UserOut:
    """
    Creates a user.

    :param request: http request
    :param object user: user data
    :return object: registered user
    :raise AlreadyExistsError: user already exists
    """

    user_id = uuid.uuid4().hex
    db['users'][user_id] = user

    return UserOut(id=user_id, **user.dict())


@specs.annotate(
    tags=['users'],
    errors=[NotFoundError],
    examples=[
        specs.MethodExample(
            summary='Simple example',
            params=dict(
                user_id='c47726c6-a232-45f1-944f-60b98966ff1b',
            ),
            result={
                 'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                 'name': 'John',
                 'surname': 'Doe',
                 'age': 25,
            },
        ),
    ],
)
@methods.add(context='request')
@validator.validate
def get_user(request: HttpRequest, user_id: uuid.UUID) -> UserOut:
    """
    Returns a user.

    :param request: http request
    :param object user_id: user id
    :return object: registered user
    :raise NotFoundError: user not found
    """

    user = db['users'].get(user_id.hex)
    if not user:
        raise NotFoundError()

    return UserOut(id=user_id, **user.dict())


@specs.annotate(
    tags=['users'],
    errors=[NotFoundError],
    examples=[
        specs.MethodExample(
            summary='Simple example',
            params=dict(
                user_id='c47726c6-a232-45f1-944f-60b98966ff1b',
            ),
            result=None,
        ),
    ],
)
@methods.add(context='request')
@validator.validate
def delete_user(request: HttpRequest, user_id: uuid.UUID) -> None:
    """
    Deletes a user.

    :param request: http request
    :param object user_id: user id
    :raise NotFoundError: user not found
    """

    user = db['users'].pop(user_id.hex, None)
    if not user:
        raise NotFoundError()
