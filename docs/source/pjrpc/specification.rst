.. _specification:

Specification
=============


``pjrpc`` has built-in `OpenAPI <https://swagger.io/specification/>`_ and `OpenRPC <https://spec.open-rpc.org/#introduction>`_
specification generation support implemented by :py:class:`pjrpc.server.specs.openapi.OpenAPI`
and :py:class:`pjrpc.server.specs.openrpc.OpenRPC` respectively.


Method description, tags, errors, examples, parameters and return value schemas can be provided by hand
using :py:func:`pjrpc.server.specs.openapi.metadata` or automatically extracted using schema extractor.
``pjrpc`` provides pydantic extractor: :py:class:`pjrpc.server.specs.extractors.pydantic.PydanticMethodInfoExtractor`.
They uses `pydantic <https://pydantic-docs.helpmanual.io/>`_ models for method summary,
description, errors, examples and schema extraction respectively. You can implement your own schema extractor
inheriting it from :py:class:`pjrpc.server.specs.extractors.BaseMethodInfoExtractor` and implementing abstract methods.

.. code-block:: python

    @methods.add(
        metadata=[
            openapi.metadata(
                tags=['users'],
                errors=[AlreadyExistsError],
            )
        ]
    )
    def add_user(user: UserIn) -> UserOut:
        """
        Creates a user.

        :param object user: user data
        :return object: registered user
        :raise AlreadyExistsError: user already exists
        """

        for existing_user in flask.current_app.users_db.values():
            if user.name == existing_user.name:
                raise AlreadyExistsError()

        user_id = uuid.uuid4().hex
        flask.current_app.users_db[user_id] = user

        return UserOut(id=user_id, **user.dict())
