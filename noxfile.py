"""Nox sessions for testing across Python versions."""

import nox

PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13", "3.14"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    session.install(".[dev]")
    session.run("pytest", *session.posargs)


@nox.session(python=PYTHON_VERSIONS[-1])
def lint(session: nox.Session) -> None:
    """Run linting checks."""
    session.install("ruff")
    session.run("ruff", "check", "src/", "tests/")
    session.run("ruff", "format", "--check", "src/", "tests/")


@nox.session(python=PYTHON_VERSIONS[-1])
def typecheck(session: nox.Session) -> None:
    """Run type checking."""
    session.install(".[dev]")
    session.run("mypy", "src/")
