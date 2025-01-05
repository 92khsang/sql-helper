# -*- coding: utf-8 -*-

import logging
import os
import shutil
from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
from pathlib import Path
from typing import (
    List,
    Optional,
    Sequence,
)

import nox
from nox.sessions import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class PythonVersion(str, Enum):
    """Supported Python versions."""
    PY310 = "3.10"
    PY311 = "3.11"
    PY312 = "3.12"


@dataclass(frozen=True)
class Config:
    """Global configuration settings."""
    PYTHON_VERSIONS: tuple[str, ...] = field(default_factory=lambda: tuple(v.value for v in PythonVersion))
    DEFAULT_VERSION: str = PythonVersion.PY312.value
    REUSE_VENV: bool = field(default_factory=lambda: bool(int(os.getenv("NOX_REUSE_VENV", "1"))))
    PROJECT_DIRS: tuple[str, ...] = ("sql_helper", "tests")
    DOCKER_COMPOSE_TIMEOUT: int = 30


CONFIG = Config()


class Poetry:
    """Poetry dependency manager."""

    @staticmethod
    def install(
        session: Session,
        groups: Optional[Sequence[str]] = None,
        *,
        no_root: bool = False
    ) -> None:
        """Install dependencies using Poetry."""
        Poetry._setup_virtual_env(session)
        Poetry._ensure_poetry_installed(session)

        cmd = ["poetry", "install", "--sync"]
        if groups:
            for group in groups:
                cmd.extend(["--with", group])
        if no_root:
            cmd.append("--no-root")

        try:
            session.run(*cmd, external=True)
        except Exception as e:
            logger.error(f"Command failed: {cmd}")
            session.error(f"Failed to install dependencies with Poetry. Error: {e}")

    @staticmethod
    def _setup_virtual_env(session: Session) -> None:
        """Configure virtualenv environment variables."""
        venv_path = Path(session.virtualenv.location)
        bin_dir = "Scripts" if os.name == "nt" else "bin"

        if not venv_path.exists():
            raise RuntimeError(f"Virtualenv not found at {venv_path}")

        session.env.update(
            {
                "VIRTUAL_ENV": str(venv_path),
                "PATH"       : os.pathsep.join([str(venv_path / bin_dir), os.environ.get("PATH", "")]),
            }
        )

    @staticmethod
    def _ensure_poetry_installed(session: Session) -> None:
        """Ensure Poetry is installed in the session."""
        try:
            session.run("poetry", "--version", external=True, silent=True, success_codes=[0])
        except Exception:
            session.run("python", "-m", "pip", "install", "poetry>=1.7.0", external=True)


def docker_compose_command(command: str) -> List[str]:
    """Generate the appropriate docker compose command based on version."""
    if shutil.which("docker-compose"):
        return ["docker-compose", command]
    elif shutil.which("docker"):
        return ["docker", "compose", command]
    else:
        raise RuntimeError("Docker Compose is not installed. Please install it to proceed.")


nox.options.sessions = ["tests", "lint", "typecheck"]


@nox.session(python=CONFIG.PYTHON_VERSIONS, reuse_venv=CONFIG.REUSE_VENV)
def tests(session: Session) -> None:
    """Run the test suite."""
    # Parse test markers from session arguments
    markers = [arg for arg in session.posargs if arg.startswith("-m")]
    if not markers:
        # Default markers if none specified
        markers = ["-m", "not slow"]  # Skip slow tests by default

    try:
        session.run(*docker_compose_command("up"), "-d", external=True)
        Poetry.install(session, groups=["test", "db"], no_root=True)

        pytest_args = [
            "--cov=sql_helper",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml",
        ]
        pytest_args.extend(markers)
        pytest_args.extend([arg for arg in session.posargs if not arg.startswith("-m")])

        session.run("pytest", *pytest_args)
    except Exception as e:
        session.error(f"Test execution failed: {e}")
    finally:
        try:
            session.run(*docker_compose_command("down"), external=True, success_codes=[0, 1])
        except Exception as e:
            logger.warning(f"Failed to stop Docker Compose: {e}")


@nox.session(python=[CONFIG.DEFAULT_VERSION], reuse_venv=CONFIG.REUSE_VENV)
def lint(session: Session) -> None:
    """Run code quality checks."""
    Poetry.install(session, groups=["dev"])
    session.run("black", "--check", *CONFIG.PROJECT_DIRS)
    session.run("ruff", "check", *CONFIG.PROJECT_DIRS)


@nox.session(python=[CONFIG.DEFAULT_VERSION], reuse_venv=CONFIG.REUSE_VENV)
def typecheck(session: Session) -> None:
    """Run static type checking."""
    Poetry.install(session, groups=["dev"])
    session.run("mypy", *CONFIG.PROJECT_DIRS)
