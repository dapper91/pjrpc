import uuid

import kombu

import pjrpc
from pjrpc.server.integration import kombu as integration

methods = pjrpc.server.MethodRegistry()


@methods.add(context='message')
def add_user(message: kombu.Message, user: dict):
    user_id = uuid.uuid4().hex

    return {'id': user_id, **user}


executor = integration.Executor('amqp://guest:guest@localhost:5672/v1', queue_name='jsonrpc')
executor.dispatcher.add_methods(methods)

if __name__ == "__main__":
    executor.run()
