"""
TODO module docstring
"""
import pkg_resources
import typing as t

from tutor import hooks


DOCKERFILE_PATCH_CONTENTS = """\
## BEGIN QUICKDEV PATCH

# Make a place for in-devlopment edx-platform packages to be mounted to
# and installed from.
VOLUME /openedx/mounted-packages

# Move node_modules out of edx-platform so that it still
# exists if edx-platform is mounted from host.
RUN mv node_modules /openedx/node_modules
RUN ln -s /openedx/node_modules

# Turn node_modules and the Python venv into named volumes so that:
# (a) they can be written to faster in the event that the
#     user wants to re-install requirements, since named volumes
#     have better write performance than both container filesystems
#     and bind-mounted volumes; and
# (b) they can be shared between all lms* and cms* containers.
# Note that the original contents of these directories, as built
# in previous steps, will be copied into the new volumes.
VOLUME /openedx/node_modules
VOLUME /openedx/venv

# TODO: fix this or remove it
# Stash dependency files so that we can compare them with edx-platform's
# files later. If they are different, then edx-platform is mounted and
# has altered dependencies, so dev-entrypoint will reinstall them.
#RUN mkdir /openedx/dependency-cache
#RUN cp package.json /openedx/dependency-cache
#RUN cp package-lock.json /openedx/dependency-cache
#RUN cp setup.py /openedx/dependency-cache
#RUN cp requirements/edx/development.txt /openedx/dependency-cache

# Put our plugin's scripts (will be mounted in docker-compose.yml) on the path.
ENV PATH /openedx/quickdev/bin:${PATH}

# Run all commands through the developer entrypoint, which
# re-installs dependencies & re-compiles assets if appropriate.
#ENTRYPOINT [ "dev-entrypoint" ]

## END QUICKDEV PATCH
"""

hooks.Filters.ENV_PATCHES.add_items(
    [
        (
            "openedx-dev-dockerfile-post-python-requirements",
            DOCKERFILE_PATCH_CONTENTS,
        ),
    ]
)


@hooks.Filters.COMPOSE_MOUNTS.add()
def _mount_edx_platform_packages(
    volumes: t.List[t.Tuple[str, str]], name: str
) -> t.List[t.Tuple[str, str]]:
    """
    When a folder named xblock-* or platform-plugin-* is mounted,
    auto-mount it to lms* & cms* containers at /openedx/mounted-packages.
    """
    if name.startswith("xblock-") or name.startswith("platform-plugin-"):
        path = f"/openedx/mounted-packages/{name}"
        volumes += [
            ("lms", path),
            ("cms", path),
            ("lms-worker", path),
            ("cms-worker", path),
            ("lms-job", path),
            ("cms-job", path),
        ]
    return volumes


EXTRA_VOLUMES: t.Dict[str, dict] = {
    "openedx_node_modules": {},  # Declare a shared volume for lms/cms node_modules.
    "openedx_venv": {},  # Declare a shared volume for lms/cms Python virtual environment.
}
EXTRA_OPENEDX_SERVICE_VOLUMES: t.List[str] = [
    "openedx_node_modules:/openedx/node_modules",  # Use shared node_modules volume.
    "openedx_venv:/openedx/venv",  # Use shared Python virtual environment.
    "../plugins/quickdev/bin:/openedx/quickdev/bin:ro",  # Bind-mount this plugin's scripts at /openedx/quickdev/bin.
]


def _add_volumes_to_services(compose_file: dict, service_names: t.List[str]) -> dict:
    """
    Given a compose file, return a new compose file where our new volumes
    are declared and added to the specified services.
    """
    _ = """services: t.Dict[str, dict] = compose_file.get("services", {})
    new_services = {}
    for service_name in service_names:
        new_services[service_name] = {
            **services,
        }
        service: dict = services.get(service_name, {})
        service["volumes"] = service.get("volumes", []) + EXTRA_OPENEDX_SERVICE_VOLUMES
        services[service_name] = service
    compose_file["services"] = services
    volumes: t.Dict[str, dict] = compose_file.get("volumes", {})
    volumes["volumes"] = {**volumes, **EXTRA_VOLUMES}"""
    services = compose_file.get("services", {})
    return {
        **compose_file,
        "volumes": {
            **compose_file.get("volumes", {}),
            **EXTRA_VOLUMES,
        },
        "services": {
            **compose_file.get("services", {}),
            **{
                service_name: {
                    **services.get(service_name, {}),
                    "volumes": [
                        *services.get(service_name, {}).get("volumes", []),
                        *EXTRA_OPENEDX_SERVICE_VOLUMES,
                    ],
                }
                for service_name in service_names
            },
        },
    }
    return compose_file


@hooks.Filters.COMPOSE_DEV_TMP.add()
def _add_volumes_to_openedx_services(docker_compose_tmp: dict) -> dict:
    return _add_volumes_to_services(
        docker_compose_tmp, ["lms", "cms", "lms-worker", "cms-worker"]
    )


@hooks.Filters.COMPOSE_DEV_JOBS_TMP.add()
def _add_volumes_to_openedx_jobs_services(docker_compose_tmp: dict) -> dict:
    return _add_volumes_to_services(docker_compose_tmp, ["lms-job", "cms-job"])


# Render any templates within tutorkdmccormick/quickdev/templates/quickdev.
# Render them directly to plugins/quickdev.
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    pkg_resources.resource_filename("tutorkdmccormick", "quickdev/templates")
)
hooks.Filters.ENV_TEMPLATE_TARGETS.add_item(("quickdev", "plugins"))
