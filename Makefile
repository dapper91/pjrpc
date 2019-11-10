.PHONY: docs

init:
	pip install pipenv --upgrade
	pipenv install --dev

test:
	pipenv run py.test

coverage:
	pipenv run py.test --verbose --cov-report term --cov=pjrpc tests

publish:
	pip install twine
	python setup.py sdist
	twine upload dist/*
	rm -fr build dist .egg requests.egg-info

docs:
	cd docs && make html
