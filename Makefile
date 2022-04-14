init:
	pip install pipenv --upgrade
	pipenv install --dev

test:
	pipenv run py.test

coverage:
	pipenv run py.test --verbose --cov-report term --cov=xjsonrpc tests

publish:
	pip install twine
	python setup.py sdist
	twine upload dist/*
	rm -fr build dist .egg requests.egg-info

check-code:
	pre-commit run --all-file

docs:
	cd docs && make html

.PHONY: docs init test coverage publish check-code
