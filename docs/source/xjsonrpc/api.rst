.. _api:

Developer Interface
===================

.. currentmodule:: xjsonrpc


.. automodule:: xjsonrpc


Common
------

.. automodule:: xjsonrpc.common
    :members:

Exceptions
~~~~~~~~~~

.. automodule:: xjsonrpc.common.exceptions
    :members:

Identifier generators
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: xjsonrpc.common.generators
    :members:


Client
------

.. automodule:: xjsonrpc.client
    :members:

Backends
~~~~~~~~

.. automodule:: xjsonrpc.client.backend.requests
    :members:

.. automodule:: xjsonrpc.client.backend.aiohttp
    :members:

.. automodule:: xjsonrpc.client.backend.kombu
    :members:

.. automodule:: xjsonrpc.client.backend.aio_pika
    :members:

Tracer
~~~~~~

.. automodule:: xjsonrpc.client.tracer
    :members:


Integrations
~~~~~~~~~~~~

.. automodule:: xjsonrpc.client.integrations.pytest
    :members:

Server
------

.. automodule:: xjsonrpc.server
    :members:


Integrations
~~~~~~~~~~~~

aiohttp
_______

.. automodule:: xjsonrpc.server.integration.aiohttp
    :members:

flask
_____

.. automodule:: xjsonrpc.server.integration.flask
    :members:

kombu
_____

.. automodule:: xjsonrpc.server.integration.kombu
    :members:

aio_pika
________

.. automodule:: xjsonrpc.server.integration.aio_pika
    :members:


werkzeug
________

.. automodule:: xjsonrpc.server.integration.werkzeug
    :members:


Validators
~~~~~~~~~~

.. automodule:: xjsonrpc.server.validators
    :members:

jsonschema
__________

.. automodule:: xjsonrpc.server.validators.jsonschema
    :members:

pydantic
________

.. automodule:: xjsonrpc.server.validators.pydantic
    :members:


Specification
~~~~~~~~~~~~~

.. automodule:: xjsonrpc.server.specs
    :members:

extractors
__________

.. automodule:: xjsonrpc.server.specs.extractors
    :members:


.. automodule:: xjsonrpc.server.specs.extractors.pydantic
    :members:


.. automodule:: xjsonrpc.server.specs.extractors.docstring
    :members:

schemas
_______


.. automodule:: xjsonrpc.server.specs.openapi
    :members:


.. automodule:: xjsonrpc.server.specs.openrpc
    :members:
