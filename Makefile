.PHONY: lint typecheck architecture test validate doctor

lint:
	nox -s lint

typecheck:
	nox -s typecheck

architecture:
	nox -s architecture

test:
	nox -s tests

validate:
	nox -s validate

doctor:
	uv run fedsira doctor
