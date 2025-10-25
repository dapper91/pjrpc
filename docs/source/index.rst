.. pjrpc documentation master file, created by
   sphinx-quickstart on Wed Oct 23 21:38:52 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python JSON-RPC without boilerplate
===================================


.. image:: https://static.pepy.tech/personalized-badge/pjrpc?period=month&units=international_system&left_color=grey&right_color=orange&left_text=Downloads/month
    :target: https://pepy.tech/project/pjrpc
    :alt: Downloads/month
.. image:: https://github.com/dapper91/pjrpc/actions/workflows/test.yml/badge.svg?branch=master
    :target: https://github.com/dapper91/pjrpc/actions/workflows/test.yml
    :alt: Build status
.. image:: https://img.shields.io/pypi/l/pjrpc.svg
    :target: https://pypi.org/project/pjrpc
    :alt: License
.. image:: https://img.shields.io/pypi/pyversions/pjrpc.svg
    :target: https://pypi.org/project/pjrpc
    :alt: Supported Python versions
.. image:: https://codecov.io/gh/dapper91/pjrpc/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/dapper91/pjrpc
    :alt: Code coverage
.. image:: https://readthedocs.org/projects/pjrpc/badge/?version=stable&style=flat
   :alt: ReadTheDocs status
   :target: https://pjrpc.readthedocs.io/en/stable/


``pjrpc`` is an extensible `JSON-RPC <https://www.jsonrpc.org>`_ client/server library with an intuitive interface
that can be easily extended and integrated in your project without writing a lot of boilerplate code.

Features:

- :doc:`framework/library agnostic <pjrpc/examples>`
- :doc:`intuitive interface <pjrpc/quickstart>`
- :doc:`extensibility <pjrpc/extending>`
- :doc:`synchronous and asynchronous client backends <pjrpc/client>`
- :doc:`popular frameworks integration <pjrpc/server>` (aiohttp, flask, aio_pika)
- :doc:`builtin parameter validation <pjrpc/validation>`
- :doc:`pytest integration <pjrpc/testing>`
- :doc:`openapi schema generation support <pjrpc/specification>`
- :doc:`openrpc schema generation support <pjrpc/specification>`
- :doc:`web ui support (SwaggerUI, RapiDoc, ReDoc) <pjrpc/webui>`


Extra requirements
------------------

- `aiohttp <https://aiohttp.readthedocs.io>`_
- `aio_pika <https://aio-pika.readthedocs.io>`_
- `flask <https://flask.palletsprojects.com>`_
- `pydantic <https://pydantic-docs.helpmanual.io/>`_
- `requests <https://requests.readthedocs.io>`_
- `httpx <https://www.python-httpx.org/>`_
- `openapi-ui-bundles <https://github.com/dapper91/python-openapi-ui-bundles>`_


The User Guide
--------------

.. toctree::
   :maxdepth: 2

   pjrpc/installation
   pjrpc/quickstart
   pjrpc/client
   pjrpc/server
   pjrpc/validation
   pjrpc/errors
   pjrpc/extending
   pjrpc/testing
   pjrpc/tracing
   pjrpc/retries
   pjrpc/specification
   pjrpc/webui
   pjrpc/examples


The API Documentation
---------------------

.. toctree::
   :maxdepth: 3

   pjrpc/api/index


Development
-----------

.. toctree::
   :maxdepth: 2

   pjrpc/development


Links
-----

- `Source code <https://github.com/dapper91/pjrpc>`_


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
