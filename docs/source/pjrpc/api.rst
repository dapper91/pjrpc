.. _api:

Developer Interface
===================

.. currentmodule:: pjrpc


.. automodule:: pjrpc


Common
------

.. automodule:: pjrpc.common
    :members:

Exceptions
~~~~~~~~~~

.. automodule:: pjrpc.common.exceptions
    :members:

Identifier generators
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: pjrpc.common.generators
    :members:


Client
------

.. automodule:: pjrpc.client
    :members:

Backends
~~~~~~~~

.. automodule:: pjrpc.client.backend.requests
    :members:

.. automodule:: pjrpc.client.backend.aiohttp
    :members:

.. automodule:: pjrpc.client.backend.kombu
    :members:

.. automodule:: pjrpc.client.backend.aio_pika
    :members:

Integrations
~~~~~~~~~~~~

.. automodule:: pjrpc.client.integrations.pytest
    :members:

Server
------

.. automodule:: pjrpc.server
    :members:


Integrations
~~~~~~~~~~~~

aiohttp
_______

.. automodule:: pjrpc.server.integration.aiohttp
    :members:

flask
_____

.. automodule:: pjrpc.server.integration.flask
    :members:

kombu
_____

.. automodule:: pjrpc.server.integration.kombu
    :members:

aio_pika
________

.. automodule:: pjrpc.server.integration.aio_pika
    :members:


werkzeug
________

.. automodule:: pjrpc.server.integration.werkzeug
    :members:


Validators
~~~~~~~~~~

.. automodule:: pjrpc.server.validators
    :members:

jsonschema
__________

.. automodule:: pjrpc.server.validators.jsonschema
    :members:

pydantic
________

.. automodule:: pjrpc.server.validators.pydantic
    :members:
