import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import fields
from typing import (
    List,
    Tuple,
)

logger = logging.getLogger(__name__)


class ConfigUtils:
    """
    Utilities for handling configuration updates.
    """

    @staticmethod
    def update_config(config, **updates):
        """
        Safely update a frozen dataclass without triggering __post_init__.

        Args:
            config: Frozen dataclass instance to update.
            **updates: Field-value pairs to update.

        Returns:
            A new dataclass instance with updated fields.
        """
        cls = config.__class__
        current_values = {field.name: getattr(config, field.name) for field in fields(config)}
        current_values.update(updates)
        obj = object.__new__(cls)
        for key, value in current_values.items():
            object.__setattr__(obj, key, value)
        return obj


class DockerUtils:
    """
    Utilities for interacting with Docker Compose and managing containers.
    """

    @staticmethod
    def get_compose_command() -> List[str]:
        """
        Determine the correct Docker Compose command.

        Returns:
            List[str]: Command for Docker Compose.
        """
        if shutil.which("docker-compose"):
            return ["docker-compose"]
        elif shutil.which("docker"):
            return ["docker", "compose"]
        raise RuntimeError("Neither 'docker compose' nor 'docker-compose' is available.")

    @staticmethod
    def run_command(command: List[str]) -> Tuple[int, str, str]:
        """
        Run a shell command and capture return code, stdout, and stderr.

        Args:
            command: List of command arguments.

        Returns:
            Tuple[int, str, str]: Return code, stdout, and stderr.
        """
        process = subprocess.run(
            command, capture_output=True, text=True,
            encoding="utf-8", errors="replace"
        )
        return process.returncode, process.stdout or "", process.stderr or ""

    @staticmethod
    def get_container_name(service_name: str) -> str:
        """
        Retrieve the actual container name using `docker compose ps`.

        Args:
            service_name: Name of the Docker Compose service.

        Returns:
            str: Container name.
        """
        compose_command = DockerUtils.get_compose_command()
        cmd = compose_command + ["ps", "--format", "json"]
        returncode, stdout, stderr = DockerUtils.run_command(cmd)

        if returncode == 0 and stdout:
            try:
                containers = json.loads(stdout)
                for container in containers:
                    if service_name in container.get('Service', ''):
                        return container.get('Name', '')
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from docker compose ps: {e}")

        project_name = os.getenv("COMPOSE_PROJECT_NAME", os.path.basename(os.getcwd()).lower())
        fallback_name = f"{project_name}-{service_name}-1"
        logger.warning(f"Falling back to container name: {fallback_name}")
        return fallback_name

    @staticmethod
    def wait_for_healthcheck(service_name: str, timeout: int = 30) -> bool:
        """
        Wait for a Docker container's health check to pass.

        Args:
            service_name: Name of the Docker Compose service.
            timeout: Timeout in seconds.

        Returns:
            bool: True if the container becomes healthy, False otherwise.
        """
        container_name = DockerUtils.get_container_name(service_name)
        logger.info(f"Waiting for container {container_name} to become healthy")

        start_time = time.time()
        while time.time() - start_time < timeout:
            cmd = ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name]
            returncode, stdout, stderr = DockerUtils.run_command(cmd)

            if returncode == 0 and stdout.strip() == "healthy":
                logger.info(f"Container {container_name} is healthy")
                return True
            elif "No such object" in stderr:
                logger.error(f"Container {container_name} not found. Restarting services...")
                up_code, _, up_err = DockerUtils.run_command(["docker", "compose", "up", "-d"])
                if up_code != 0:
                    logger.error(f"Failed to restart services: {up_err}")
                    return False

            time.sleep(1)

        logger.error(f"Container {container_name} did not become healthy within {timeout} seconds")
        return False
