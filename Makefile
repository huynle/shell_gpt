.ONESHELL:

venv:
	python3 -m venv venv

install-local: venv
	pip3 install --user -e . 

dev: venv
	. venv/bin/activate
	pip3 install -e .[test,dev]

test: venv
	. venv/bin/activate
	bash ./scripts/test.sh
