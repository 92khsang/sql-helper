import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import (
    AsyncGenerator,
    Generator,
    List,
)

import pytest
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from sql_helper.database import Database
from sql_helper.database.config import (
    DatabaseConfig,
    DatabaseCredentials,
)
from sql_helper.database.types import DatabaseType

# Test credentials for all databases
TEST_CREDENTIALS = DatabaseCredentials(
    username="test_user",
    password="test_password"
)

# Configure logger
logger = logging.getLogger(__name__)


def get_compose_command() -> List[str]:
    """Determine the correct docker compose command."""
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    elif shutil.which("docker"):
        return ["docker", "compose"]
    else:
        raise RuntimeError("Neither 'docker compose' nor 'docker-compose' is available.")


def run_command(command: List[str]) -> tuple[int, str, str]:
    """Run a shell command and capture returncode, stdout, stderr."""
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return process.returncode, process.stdout or "", process.stderr or ""


def get_container_name(service_name: str) -> str:
    """Retrieve the actual container name using `docker compose ps`."""
    compose_command = get_compose_command()
    cmd = compose_command + ["ps", "--format", "json"]
    returncode, stdout, stderr = run_command(cmd)

    if returncode == 0 and stdout:
        try:
            containers = json.loads(stdout)
            for container in containers:
                if service_name in container.get('Service', ''):
                    logger.info(f"Found container: {container}")
                    return container.get('Name', '')
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from docker compose ps: {e}")
    else:
        logger.error(f"Failed to execute 'docker compose ps': {stderr}")

    # Fallback to guessed container name using project name
    project_name = os.getenv("COMPOSE_PROJECT_NAME", os.path.basename(os.getcwd()).lower())
    fallback_name = f"{project_name}-{service_name}-1"
    logger.warning(f"Falling back to container name: {fallback_name}")
    return fallback_name


def wait_for_healthcheck(service_name: str, timeout: int = 30) -> bool:
    """Wait for Docker container healthcheck to pass."""
    container_name = get_container_name(service_name)
    logger.info(f"Waiting for container {container_name} to become healthy")

    start_time = time.time()
    while time.time() - start_time < timeout:
        cmd = ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name]
        returncode, stdout, stderr = run_command(cmd)

        logger.debug(f"Inspect command result: returncode={returncode}, stdout={stdout}, stderr={stderr}")

        if returncode == 0 and stdout.strip() == "healthy":
            logger.info(f"Container {container_name} is healthy")
            return True
        elif "No such object" in stderr:
            logger.error(f"Container {container_name} not found. Restarting services...")
            up_code, _, up_err = run_command(["docker", "compose", "up", "-d"])
            if up_code != 0:
                logger.error(f"Failed to restart services: {up_err}")
                return False

        time.sleep(1)

    logger.error(f"Container {container_name} did not become healthy within {timeout} seconds")
    return False


@pytest.fixture(scope="session", autouse=True)
def database_setup():
    """Master fixture for database setup."""
    # First wait for containers to be healthy
    containers = ["postgres", "mysql", "mariadb"]
    for container in containers:
        if not wait_for_healthcheck(container):
            pytest.fail(f"Container {container} did not become healthy")

    # Finally initialize schemas
    init_scripts = {
        "postgresql+psycopg://test_user:test_password@localhost:5433/test_db": """  
            CREATE TABLE IF NOT EXISTS test_table (  
                id SERIAL PRIMARY KEY,  
                value TEXT  
            );  
        """,
        "mysql+pymysql://test_user:test_password@localhost:3307/test_db"     : """  
            CREATE TABLE IF NOT EXISTS test_table (  
                id INT AUTO_INCREMENT PRIMARY KEY,  
                value TEXT  
            );  
        """,
        "mysql+pymysql://test_user:test_password@localhost:3308/test_db"     : """  
            CREATE TABLE IF NOT EXISTS test_table (  
                id INT AUTO_INCREMENT PRIMARY KEY,  
                value TEXT  
            );  
        """
    }

    for url, script in init_scripts.items():
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text(script))
                conn.commit()
        except Exception as e:
            pytest.fail(f"Database initialization failed for {url}")


@pytest.fixture(scope="session")
def event_loop_policy():
    """Configure event loop policy for Windows compatibility."""
    if sys.platform == 'win32':
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def postgres_config() -> DatabaseConfig:
    """Create PostgreSQL test configuration."""
    return DatabaseConfig(
        type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5433,
        database="test_db",
        credentials=TEST_CREDENTIALS,
        enable_async=True
    )


@pytest.fixture(scope="session")
def mysql_config() -> DatabaseConfig:
    """Create MySQL test configuration."""
    return DatabaseConfig(
        type=DatabaseType.MYSQL,
        host="localhost",
        port=3307,
        database="test_db",
        credentials=TEST_CREDENTIALS,
        enable_async=True
    )


@pytest.fixture(scope="session")
def mariadb_config() -> DatabaseConfig:
    """Create MariaDB test configuration."""
    return DatabaseConfig(
        type=DatabaseType.MARIADB,
        host="localhost",
        port=3308,
        database="test_db",
        credentials=TEST_CREDENTIALS,
        enable_async=True
    )


@pytest.fixture(params=["postgres_config", "mysql_config", "mariadb_config"])
def database_config(request) -> DatabaseConfig:
    """Parametrized fixture for all database configurations."""
    return request.getfixturevalue(request.param)


@pytest.fixture
def db(database_config: DatabaseConfig) -> Generator[Database, None, None]:
    """Create and dispose Database instance for each test."""
    database = Database(database_config)
    yield database
    database.dispose_sync()


@pytest.fixture
async def async_db(database_config: DatabaseConfig) -> AsyncGenerator[Database, None]:
    """Create and dispose async Database instance for each test."""
    database = Database(database_config)
    yield database
    await database.dispose_async()


@pytest.fixture
def sync_session(db: Database) -> Generator[Session, None, None]:
    """Create a synchronous database session."""
    with db.get_db() as session:
        yield session


@pytest.fixture
async def async_session(async_db: Database) -> AsyncGenerator[AsyncSession, None]:
    """Create an asynchronous database session."""
    async with async_db.get_async_db() as session:
        yield session
