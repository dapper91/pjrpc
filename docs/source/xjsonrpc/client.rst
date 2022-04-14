.. _client:

Client
======


``xjsonrpc`` client provides three main method invocation approaches:

- using handmade :py:class:`xjsonrpc.common.Request` class object

.. code-block:: python

    client = Client('http://server/api/v1')

    response: xjsonrpc.Response = client.send(Request('sum', params=[1, 2], id=1))
    print(f"1 + 2 = {response.result}")


- using ``__call__`` method

.. code-block:: python

    client = Client('http://server/api/v1')

    result = client('sum', a=1, b=2)
    print(f"1 + 2 = {result}")

- using proxy object

.. code-block:: python

    client = Client('http://server/api/v1')

    result = client.proxy.sum(1, 2)
    print(f"1 + 2 = {result}")

.. code-block:: python

    client = Client('http://server/api/v1')

    result = client.proxy.sum(a=1, b=2)
    print(f"1 + 2 = {result}")

Requests without id in JSON-RPC semantics called notifications. To send a notification to the server
you need to send a request without id:

.. code-block:: python

    client = Client('http://server/api/v1')

    response: xjsonrpc.Response = client.send(Request('sum', params=[1, 2]))


or use a special method :py:meth:`xjsonrpc.client.AbstractClient.notify`

.. code-block:: python

    client = Client('http://server/api/v1')
    client.notify('tick')


Asynchronous client api looks pretty much the same:

.. code-block:: python

    client = Client('http://server/api/v1')

    result = await client.proxy.sum(1, 2)
    print(f"1 + 2 = {result}")


Batch requests
--------------

Batch requests also supported. There are several approaches of sending batch requests:

- using handmade :py:class:`xjsonrpc.common.Request` class object. The result is a :py:class:`xjsonrpc.common.BatchResponse`
  instance you can iterate over to get all the results or get each one by index:

.. code-block:: python

    client = Client('http://server/api/v1')

    batch_response = client.batch.send(BatchRequest(
        xjsonrpc.Request('sum', [2, 2], id=1),
        xjsonrpc.Request('sub', [2, 2], id=2),
        xjsonrpc.Request('div', [2, 2], id=3),
        xjsonrpc.Request('mult', [2, 2], id=4),
    ))
    print(f"2 + 2 = {batch_response[0].result}")
    print(f"2 - 2 = {batch_response[1].result}")
    print(f"2 / 2 = {batch_response[2].result}")
    print(f"2 * 2 = {batch_response[3].result}")


- using ``__call__`` method chain:

.. code-block:: python

    client = Client('http://server/api/v1')

    result = client.batch('sum', 2, 2)('sub', 2, 2)('div', 2, 2)('mult', 2, 2).call()
    print(f"2 + 2 = {result[0]}")
    print(f"2 - 2 = {result[1]}")
    print(f"2 / 2 = {result[2]}")
    print(f"2 * 2 = {result[3]}")


- using subscription operator:

.. code-block:: python

    client = Client('http://server/api/v1')

    result = client.batch[
        ('sum', 2, 2),
        ('sub', 2, 2),
        ('div', 2, 2),
        ('mult', 2, 2),
    ]
    print(f"2 + 2 = {result[0]}")
    print(f"2 - 2 = {result[1]}")
    print(f"2 / 2 = {result[2]}")
    print(f"2 * 2 = {result[3]}")


- using proxy chain call:

.. code-block:: python

    client = Client('http://server/api/v1')

    result = client.batch.proxy.sum(2, 2).sub(2, 2).div(2, 2).mult(2, 2).call()
    print(f"2 + 2 = {result[0]}")
    print(f"2 - 2 = {result[1]}")
    print(f"2 / 2 = {result[2]}")
    print(f"2 * 2 = {result[3]}")


Which one to use is up to you but be aware that if any of the requests returns an error the result of the other ones
will be lost. In such case the first approach can be used to iterate over all the responses and get the results of
the succeeded ones like this:

.. code-block:: python

    import xjsonrpc
    from xjsonrpc.client.backend import requests as xjsonrpc_client


    client = xjsonrpc_client.Client('http://localhost/api/v1')

    batch_response = client.batch.send(xjsonrpc.BatchRequest(
        xjsonrpc.Request('sum', [2, 2], id=1),
        xjsonrpc.Request('sub', [2, 2], id=2),
        xjsonrpc.Request('div', [2, 2], id=3),
        xjsonrpc.Request('mult', [2, 2], id=4),
    ))

    for response in batch_response:
        if response.is_success:
            print(response.result)
        else:
            print(response.error)


Notifications also supported:

.. code-block:: python

    import xjsonrpc
    from xjsonrpc.client.backend import requests as xjsonrpc_client


    client = xjsonrpc_client.Client('http://localhost/api/v1')

    client.batch.notify('tick').notify('tack').notify('tick').notify('tack').call()



Id generators
--------------

The library request id generator can also be customized. There are four generator types implemented in the library
see :py:mod:`xjsonrpc.common.generators`. You can implement your own one and pass it to a client by `id_gen`
parameter.
