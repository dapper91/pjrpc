import uuid
from collections import defaultdict

import pydantic
from django.http.request import HttpRequest

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.specs import openapi as specs
from pjrpc.server.validators import pydantic as validators

methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()
db = defaultdict(dict)


class PostIn(pydantic.BaseModel):
    """
    Post data.
    """

    title: str
    content: str


class PostOut(PostIn):
    """
    Created post data.
    """

    id: uuid.UUID


class AlreadyExistsError(pjrpc.exc.JsonRpcError):
    """
    Post already registered error.
    """

    code = 2003
    message = "post already exists"


class NotFoundError(pjrpc.exc.JsonRpcError):
    """
    Post not found error.
    """

    code = 2004
    message = "post not found"


@specs.annotate(
    tags=['posts'],
    errors=[AlreadyExistsError],
    examples=[
        specs.MethodExample(
            summary="Simple example",
            params=dict(
                post={
                    'title': 'Super post',
                    'content': 'My first post',
                },
            ),
            result={
                'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                'title': 'Super post',
                'content': 'My first post',
            },
        ),
    ],
)
@methods.add(context='request')
@validator.validate
def add_post(request: HttpRequest, post: PostIn) -> PostOut:
    """
    Creates a post.

    :param request: http request
    :param object post: post data
    :return object: created post
    :raise AlreadyExistsError: post already exists
    """

    post_id = uuid.uuid4().hex
    db['posts'][post_id] = post

    return PostOut(id=post_id, **post.model_dump())


@specs.annotate(
    tags=['posts'],
    errors=[NotFoundError],
    examples=[
        specs.MethodExample(
            summary="Simple example",
            params=dict(
                post_id='c47726c6-a232-45f1-944f-60b98966ff1b',
            ),
            result={
                'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                'title': 'Super post',
                'content': 'My first post',
            },
        ),
    ],
)
@methods.add(context='request')
@validator.validate
def get_post(request: HttpRequest, post_id: uuid.UUID) -> PostOut:
    """
    Returns a post.

    :param request: http request
    :param object post_id: post id
    :return object: registered post
    :raise NotFoundError: post not found
    """

    post = db['posts'].get(post_id)
    if not post:
        raise NotFoundError()

    return PostOut(**post.model_dump())


@specs.annotate(
    tags=['posts'],
    errors=[NotFoundError],
    examples=[
        specs.MethodExample(
            summary='Simple example',
            params=dict(
                post_id='c47726c6-a232-45f1-944f-60b98966ff1b',
            ),
            result=None,
        ),
    ],
)
@methods.add(context='request')
@validator.validate
def delete_post(request: HttpRequest, post_id: uuid.UUID) -> None:
    """
    Deletes a post.

    :param request: http request
    :param object post_id: post id
    :raise NotFoundError: post not found
    """

    post = db['posts'].pop(post_id, None)
    if not post:
        raise NotFoundError()
