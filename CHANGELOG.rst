Changelog
=========

1.11.0 (2024-12-08)
------------------

- added exclude_param argument to be able to exclude a json-rpc parameter from validation and schema extraction.


1.10.1 (2024-11-13)
------------------

- minor bugfixes


1.10.0 (2024-11-12)
------------------

- openapi 3.x support added.
- batch size validation support added.
- custom http server response status added.
- raise_for_status flag added for http clients.
- python 3.12, 3.13 support added.


1.9.0 (2024-04-22)
------------------

- aio-pika custom response exchange support added.


1.8.3 (2023-12-15)
------------------

- aiohttp client uses request context manager.


1.8.2 (2023-12-07)
------------------

- openapi schema generation bug fixed.


1.8.1 (2023-11-28)
------------------

- client headers passing bug fixed.


1.8.0 (2023-09-26)
------------------

- pydantic 2 support added


1.7.0 (2023-08-10)
------------------

- refactoring done
- dependencies updated
- python 3.11 support added


1.6.0 (2022-07-05)
------------------

- JSON-RPC client requests retry support added
- aio-pika integration and backend updated for aio-pika 8.0
- type aliases for middlewares added
- httpx minimal version updated due to found vulnerability


1.5.0 (2022-05-22)
------------------

- python 3.10 support added
- pipenv replaced by poetry
- mypy type checker added
- kombu client hanging bug fixed
- openapi json-rpc versions reordered so that version 2.0 will be the default example version
- set_default_content_type function exposed
- documentation fixed

1.4.1 (2022-03-06)
------------------

- pytest integration fixed to make asynchronous methods pass-through possible.


1.4.0 (2021-11-30)
------------------

- openapi error examples support added.
- openapi errors schema support added.
- multiple extractors support added.
- docstring extractor bug fixed.


1.3.5 (2021-11-03)
------------------

- request and response loggers separated.
- alternative json-rpc content types support added.


1.3.4 (2021-09-11)
------------------

- openapi dataclass alias setting bug fixed.


1.3.3 (2021-09-10)
------------------

- openapi jsonrpc request schema fixed


1.3.2 (2021-08-30)
------------------

- starlette integration added
- django integration added
- sub endpoints support implemented


1.3.1 (2021-08-24)
------------------

- pytest integration bug fixed
- ViewMethod copy bug fixed
- pydantic required version increased
- openapi/openrpc specification definitions support implemented


1.3.0 (2021-08-13)
------------------

- openapi specification generation implemented
- openrpc specification generation implemented
- web ui support added (SwaggerUI, RapiDoc, ReDoc)


1.2.3 (2021-08-10)
------------------

- pydantic schema generation bug fixed
- method registry merge implementation changed


1.2.2 (2021-07-28)
------------------

- pydantic validation schema bug fixed
- method registry merge bug fixed
- method view validation bug fixed
- method metadata format changed


1.2.1 (2021-03-02)
------------------

- some trash removed


1.2.0 (2021-03-01)
------------------

- httpx integration added


1.1.1 (2020-10-25)
------------------

- dependencies updated


1.1.0 (2020-03-28)
------------------

- type annotations added


1.0.0 (2020-03-14)
------------------

- middleware support implemented
- client tracing implemented
- aiohttp server backend refactored
- validation error json serialization fix
- request dispatcher refactored


0.1.4 (2019-12-10)
------------------

- aio-pika and kombu integration refactoring
- async dispatcher concurrent methods execution implemented


0.1.3 (2019-11-10)
------------------

- Some bugs fixed
- Documentation completed


0.1.2 (2019-11-10)
------------------

- Some unit tests added


0.1.1 (2019-11-09)
------------------

- Some minor fixes


0.1.0 (2019-10-23)
------------------

- Initial release
