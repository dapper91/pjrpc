
init:
	pip install poetry --upgrade
	poetry install --no-root

test:
	poetry run py.test

coverage:
	poetry run py.test --verbose --cov-report term --cov=pjrpc tests

check-code:
	pre-commit run --all-file

docs:
	cd docs && make html

.PHONY: docs init test coverage publish check-code
