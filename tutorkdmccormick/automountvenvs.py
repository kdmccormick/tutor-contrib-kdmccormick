"""
A Tutor plugin to auto-mount folders prefixed with "venv-" as virtualenvs
in various Tutor services.
"""
from typing import List, Tuple

from tutor import hooks


@hooks.Filters.COMPOSE_MOUNTS.add()
def _auto_mount_venvs(volumes: List[Tuple[str, str]], name: str):
    """
    If the given folder (`name`) is in the form "venv-<service>",
    then mount it at /openedx/venv in <service> as well as <service>-job.

    In the special case of "venv-openedx", mount the folder at /openedx/venv
    for both lms & cms, as well as their -worker variants and their -job variants.

    Will cause a downstream error if <service> is not a valid service.
    """
    if name.startswith("venv-"):
        path = "/openedx/venv"
        service = name.split("venv-")[1]
        if service == "openedx":
            volumes += [
                ("lms", path),
                ("lms-job", path),
                ("lms-worker", path),
                ("cms", path),
                ("cms-job", path),
                ("cms-worker", path),
            ]
        else:
            volumes += [
                (service, path),
                (f"{service}-job", path),
            ]
    return volumes
