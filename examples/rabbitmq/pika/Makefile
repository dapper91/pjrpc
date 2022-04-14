# Makefile to (re)start the rabbitmq container:
# docker-compose -f examples/rabbitmq/pika/docker-compose.yml

DOCKER_COMPOSE_YAML = $(dir $(MAKEFILE_LIST))docker-compose.yml
DOCKER_COMPOSE = docker-compose -f $(DOCKER_COMPOSE_YAML)

CONTAINER = pika_rabbit_1
DOCKER_EXEC = docker exec -it $(CONTAINER)

# To execute this example, run: make restart-rabbitmq-container
# - Then start the server and the client

restart-rabbitmq-container:
	$(DOCKER_COMPOSE) kill
	$(DOCKER_COMPOSE) up --detach
	@echo
	@echo 'You should be ready to start the server and the client now.'
	@echo
	@echo 'For development, server and client use the notification'
	@echo '"schedule_shutdown" to shutdown the server after each run.'
	@echo
	@echo 'When changing a server, run the client in a while loop.'
	@echo 'Likewise, when changing the client, run the server in a loop.'

# Development rules:

# To delete the jsonrpc queue to force the server to recreate it, use:
delete-queue:
	$(DOCKER_EXEC) rabbitmqadmin delete queue name jsonrpc