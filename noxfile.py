import nox

nox.options.reuse_existing_virtualenvs = True

PYTHON = "3.11"


@nox.session(python=PYTHON)
def lint(session: nox.Session) -> None:
    session.install("-e", ".")
    session.install("ruff")
    session.run("ruff", "format", "--check", ".")
    session.run("ruff", "check", ".")


@nox.session(python=PYTHON)
def typecheck(session: nox.Session) -> None:
    session.install("-e", ".")
    session.install("pyright")
    session.run("pyright")


@nox.session(python=PYTHON)
def architecture(session: nox.Session) -> None:
    session.install("-e", ".")
    session.install("pytest", "vulture", "lint-imports")
    session.run("pytest", "tests/architecture", "-x")


@nox.session(python=PYTHON)
def dependency_hygiene(session: nox.Session) -> None:
    session.install("-e", ".")
    session.install("deptry")
    session.run("deptry", "src")


@nox.session(python=PYTHON)
def tests(session: nox.Session) -> None:
    session.install("-e", ".")
    session.install("pytest")
    session.run("pytest", "tests", "-x")


@nox.session(python=PYTHON)
def validate(session: nox.Session) -> None:
    session.notify("lint")
    session.notify("typecheck")
    session.notify("architecture")
    session.notify("dependency_hygiene")
    session.notify("tests")
