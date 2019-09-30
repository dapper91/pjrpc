.. pjrpc documentation master file, created by
   sphinx-quickstart on Wed Oct 23 21:38:52 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pjrpc's documentation!
=================================


.. image:: https://travis-ci.org/dapper91/pjrpc.svg?branch=master
    :target: https://travis-ci.org/dapper91/pjrpc
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


``pjrpc`` is a flexible `JSON-RPC <https://www.jsonrpc.org>`_ client/server library that provides a very
intuitive interface and can be extended without writing boilerplate code.

Features:

- intuitive interface
- extendability
- synchronous and asynchronous client backed
- popular frameworks integration
- builtin parameter validation
- pytest integration


Extra requirements
------------------

- `aiohttp <https://aiohttp.readthedocs.io>`_
- `flask <https://flask.palletsprojects.com>`_
- `jsonschema <https://python-jsonschema.readthedocs.io>`_
- `pydantic <https://pydantic-docs.helpmanual.io/>`_
- `requests <https://requests.readthedocs.io>`_


The User Guide
--------------

.. toctree::
   :maxdepth: 2

   pjrpc/installation
   pjrpc/quickstart


The API Documentation
---------------------

.. toctree::
   :maxdepth: 3

   pjrpc/api


Development
-----------

.. toctree::
   :maxdepth: 2

   pjrpc/development


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
