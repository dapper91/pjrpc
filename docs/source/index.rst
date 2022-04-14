.. xjsonrpc documentation master file, created by
   sphinx-quickstart on Wed Oct 23 21:38:52 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to xjsonrpc's documentation!
=================================


.. image:: https://static.pepy.tech/personalized-badge/xjsonrpc?period=month&units=international_system&left_color=grey&right_color=orange&left_text=Downloads/month
    :target: https://pepy.tech/project/xjsonrpc
    :alt: Downloads/month
.. image:: https://travis-ci.org/bernhardkaindl/xjsonrpc.svg?branch=master
    :target: https://travis-ci.org/bernhardkaindl/xjsonrpc
    :alt: Build status
.. image:: https://img.shields.io/pypi/l/xjsonrpc.svg
    :target: https://pypi.org/project/xjsonrpc
    :alt: License
.. image:: https://img.shields.io/pypi/pyversions/xjsonrpc.svg
    :target: https://pypi.org/project/xjsonrpc
    :alt: Supported Python versions
.. image:: https://codecov.io/gh/bernhardkaindl/xjsonrpc/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/bernhardkaindl/xjsonrpc
    :alt: Code coverage
.. image:: https://readthedocs.org/projects/xjsonrpc/badge/?version=stable&style=flat
   :alt: ReadTheDocs status
   :target: https://xjsonrpc.readthedocs.io/en/stable/


``xjsonrpc`` is an extensible `JSON-RPC <https://www.jsonrpc.org>`_ client/server library with an intuitive interface
that can be easily extended and integrated in your project without writing a lot of boilerplate code.

Features:

- :doc:`framework/library agnostic <xjsonrpc/examples>`
- :doc:`intuitive interface <xjsonrpc/quickstart>`
- :doc:`extensibility <xjsonrpc/extending>`
- :doc:`synchronous and asynchronous client backends <xjsonrpc/client>`
- :doc:`popular frameworks integration <xjsonrpc/server>` (aiohttp, flask, kombu, aio_pika)
- :doc:`builtin parameter validation <xjsonrpc/validation>`
- :doc:`pytest integration <xjsonrpc/testing>`
- :doc:`openapi schema generation support <xjsonrpc/specification>`
- :doc:`openrpc schema generation support <xjsonrpc/specification>`
- :doc:`web ui support (SwaggerUI, RapiDoc, ReDoc) <xjsonrpc/webui>`


Extra requirements
------------------

- `aiohttp <https://aiohttp.readthedocs.io>`_
- `aio_pika <https://aio-pika.readthedocs.io>`_
- `flask <https://flask.palletsprojects.com>`_
- `jsonschema <https://python-jsonschema.readthedocs.io>`_
- `kombu <https://kombu.readthedocs.io/en/stable/>`_
- `pydantic <https://pydantic-docs.helpmanual.io/>`_
- `requests <https://requests.readthedocs.io>`_
- `httpx <https://www.python-httpx.org/>`_
- `openapi-ui-bundles <https://github.com/dapper91/python-openapi-ui-bundles>`_
- `starlette <https://www.starlette.io/>`_
- `django <https://www.djangoproject.com>`_


The User Guide
--------------

.. toctree::
   :maxdepth: 2

   xjsonrpc/installation
   xjsonrpc/quickstart
   xjsonrpc/client
   xjsonrpc/server
   xjsonrpc/validation
   xjsonrpc/errors
   xjsonrpc/extending
   xjsonrpc/testing
   xjsonrpc/tracing
   xjsonrpc/specification
   xjsonrpc/webui
   xjsonrpc/examples


The API Documentation
---------------------

.. toctree::
   :maxdepth: 3

   xjsonrpc/api


Development
-----------

.. toctree::
   :maxdepth: 2

   xjsonrpc/development


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
