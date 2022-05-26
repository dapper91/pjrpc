
init:
	pip install poetry --upgrade
	@# Updates poetry.lock in case pyproject.toml was updated for install:
	poetry update

# For tests to always find pjrpc and other test modules, PYTHONPATH is needed:
export PYTHONPATH=$(CURDIR)
export PYTHONWARNINGS=ignore::DeprecationWarning
test:
	poetry run py.test

coverage:
	poetry run py.test --verbose --cov-report term --cov=pjrpc tests

check-code:
	pre-commit run --all-file

docs:
	cd docs && make html

.PHONY: docs init test coverage publish check-code
