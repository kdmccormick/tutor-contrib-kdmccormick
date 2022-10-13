"""
TODO
"""
import pkg_resources
import typing as t

from tutor import hooks


@hooks.Filters.COMPOSE_MOUNTS.add()
def _mount_edx_platform_packages(
    volumes: t.List[t.Tuple[str, str]], name: str
) -> t.List[t.Tuple[str, str]]:
    """
    TODO
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


DOCKERFILE_PATCH_CONTENTS = """\
######## BEGIN DEV WORKFLOW EXPERIMENTATION #########

# Make a place for in-devlopment edx-platform packages to be mounted to
# and installed from.
RUN mkdir /openedx/mounted-packages

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
VOLUME /openedx/node_modules
VOLUME /openedx/venv

# Stash dependency files so that we can compare them with edx-platform's
# files later. If they are different, then edx-platform is mounted and
# has altered dependencies, so dev-entrypoint will reinstall them.
#RUN mkdir /openedx/dependency-cache
#RUN cp package.json /openedx/dependency-cache
#RUN cp package-lock.json /openedx/dependency-cache
#RUN cp setup.py /openedx/dependency-cache
#RUN cp requirements/edx/development.txt /openedx/dependency-cache

# Put our plugin's scripts (will be mounted in docker-compose.yml) on the path.
ENV PATH /openedx/deventrypoint/bin:${PATH}

# Run all commands through the developer entrypoint, which
# re-installs dependencies & re-compiles assets if appropriate.
#ENTRYPOINT [ "dev-entrypoint" ]

######## END DEV WORKFLOW EXPERIMENTATION #########
"""

EXTRA_VOLUMES = {"openedx_node_modules": {}, "openedx_venv": {}}
EXTRA_OPENEDX_SERVICE_VOLUMES = [
    "openedx_node_modules:/openedx/node_modules",
    "openedx_venv:/openedx/venv",
    "../plugins/deventrypoint/bin:/openedx/deventrypoint/bin:ro",
]

@hooks.Filters.COMPOSE_DEV_TMP.add()
def _mount_script(docker_compose_tmp):
    services = docker_compose_tmp.get("services", [])
    for svc in ["lms", "cms", "lms-worker", "cms-worker"]:
        service = services.get(svc, {})
        service["volumes"] = service.get("volumes", []) + EXTRA_OPENEDX_SERVICE_VOLUMES
        services[svc] = service
    docker_compose_tmp["services"] = services
    volumes = docker_compose_tmp.get("volumes", {})
    docker_compose_tmp["volumes"] = {**volumes, **EXTRA_VOLUMES}
    return docker_compose_tmp

@hooks.Filters.COMPOSE_DEV_JOBS_TMP.add()
def _mount_script_jobs(docker_compose_tmp):
    services = docker_compose_tmp.get("services", [])
    for svc in ["lms-job", "cms-job"]:
        service = services.get(svc, {})
        service["volumes"] = service.get("volumes", []) + EXTRA_OPENEDX_SERVICE_VOLUMES
        services[svc] = service
    docker_compose_tmp["services"] = services
    volumes = docker_compose_tmp.get("volumes", {})
    docker_compose_tmp["volumes"] = {**volumes, **EXTRA_VOLUMES}
    return docker_compose_tmp

    
hooks.Filters.ENV_PATCHES.add_items(
    [
        (
            "openedx-dev-dockerfile-post-python-requirements",
            DOCKERFILE_PATCH_CONTENTS,
        ),
    ]
)

# Render any templates within tutorkdmccormick/deventrpoint/templates/deventrypoint.
# Render them directly to plugins/deventrypoint.
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    pkg_resources.resource_filename("tutorkdmccormick", "deventrypoint/templates")
)
hooks.Filters.ENV_TEMPLATE_TARGETS.add_item(
    ("deventrypoint", "plugins")
)

