import logging
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root: Path) -> Path:
    """Return the test data directory."""
    return project_root / "tests" / "data"


@pytest.fixture
def ssl_temp_files(tmp_path):
    """Fixture to create temporary SSL certificate files."""
    ca_cert = tmp_path / "ca.pem"
    client_cert = tmp_path / "client-cert.pem"
    client_key = tmp_path / "client-key.pem"
    ca_cert.write_text("mock_ca_cert_content")
    client_cert.write_text("mock_client_cert_content")
    client_key.write_text("mock_client_key_content")

    return {
        "ca_cert"    : str(ca_cert),
        "client_cert": str(client_cert),
        "client_key" : str(client_key),
    }


class IgnoreTestErrors(logging.Filter):
    """Filter out 'Intentional error' messages."""

    def filter(self, record):
        return "Intentional error" not in record.getMessage()


def pytest_configure(config):
    """Configure logging for sql_helper module."""
    module_logger = logging.getLogger("sql_helper")

    log_level = config.getoption("--log-cli-level", default="CRITICAL")
    if not isinstance(log_level, str):
        log_level = "CRITICAL"

    module_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in module_logger.handlers:
        module_logger.removeHandler(handler)

    # Add a new StreamHandler with custom formatting
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    module_logger.addHandler(handler)

    # Add filter to ignore specific errors
    module_logger.addFilter(IgnoreTestErrors())


def pytest_collection_modifyitems(config, items):
    """Automatically add markers based on directory structure."""
    for item in items:
        # Get the relative path of the test file
        test_path = Path(item.fspath).relative_to(config.rootdir / "tests")
        test_path_str = str(test_path).replace("\\", "/")  # Ensure compatibility on Windows

        # Add 'unit' marker for files under 'tests/unit'
        if test_path_str.startswith("unit/"):
            item.add_marker(pytest.mark.unit)

        # Add 'integration' marker for files under 'tests/integration'
        elif test_path_str.startswith("integration/"):
            item.add_marker(pytest.mark.integration)

        # Add 'database' marker for files in 'database' subdirectory
        if "database" in test_path_str:
            item.add_marker(pytest.mark.database)
