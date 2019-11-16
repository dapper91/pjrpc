.. _validation:

Validation
==========


Very often besides dumb method parameters validation you need to implement more "deep" validation and provide
comprehensive errors description to your clients. Fortunately ``pjrpc`` has builtin parameter validation based on
`pydantic <https://pydantic-docs.helpmanual.io/>`_ library which uses python type annotation based validation.
Look at the following example. All you need to annotate method parameters (or describe more complex type if necessary),
that's it. ``pjrpc`` will be validating method parameters and returning informative errors to clients:

.. code-block:: python

    import enum
    import uuid
    from typing import List

    import pydantic
    from aiohttp import web

    import pjrpc.server
    from pjrpc.server.validators import pydantic as validators
    from pjrpc.server.integration import aiohttp

    methods = pjrpc.server.MethodRegistry()
    validator = validators.PydanticValidator()


    class ContactType(enum.Enum):
        PHONE = 'phone'
        EMAIL = 'email'


    class Contact(pydantic.BaseModel):
        type: ContactType
        value: str


    class User(pydantic.BaseModel):
        name: str
        surname: str
        age: int
        contacts: List[Contact]


    @methods.add(context='request')
    @validator.validate
    async def add_user(request: web.Request, user: User):
        user_id = uuid.uuid4()
        request.app['users'][user_id] = user

        return {'id': user_id, **user.dict()}


    class JSONEncoder(pjrpc.common.JSONEncoder):

        def default(self, o):
            if isinstance(o, uuid.UUID):
                return o.hex
            if isinstance(o, enum.Enum):
                return o.value

            return super().default(o)


    app = aiohttp.Application('/api/v1', json_encoder=JSONEncoder)
    app.dispatcher.add_methods(methods)
    app['users'] = {}

    if __name__ == "__main__":
        web.run_app(app, host='localhost', port=8080)


The library also supports :py:mod:`pjrpc.server.validators.jsonschema` validator. In case you like any other
validation library/framework it can be easily integrated in ``pjrpc`` library.
