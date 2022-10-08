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

# Stash dependency files so that we can compare them with edx-platform's
# files later. If they are different, then edx-platform is mounted and
# has altered dependencies, so dev-entrypoint will reinstall them.
RUN mkdir /openedx/dependency-cache
RUN cp package.json /openedx/dependency-cache
RUN cp package-lock.json /openedx/dependency-cache
RUN cp requirements/edx/development.txt /openedx/dependency-cache

# Run all commands through the developer entrypoint, which
# re-installs dependencies & re-compiles assets if appropriate.
ENTRYPOINT [ "bash", "/openedx/deventrypoint/dev-entrypoint" ]

######## END DEV WORKFLOW EXPERIMENTATION #########
"""

MOUNT_SPECIFIER = "../plugins/deventrypoint/mounts:/openedx/deventrypoint:ro"
DOCKER_COMPOSE_PATCH_CONTENTS = f"""\
lms:
  volumes:
    - {MOUNT_SPECIFIER} 
cms:
  volumes:
    - {MOUNT_SPECIFIER} 
lms-worker:
  volumes:
    - {MOUNT_SPECIFIER} 
cms-worker:
  volumes:
    - {MOUNT_SPECIFIER} 
"""
DOCKER_COMPOSE_JOBS_PATCH_CONTENTS = f"""\
lms-job:
  volumes:
    - {MOUNT_SPECIFIER} 
cms-job:
  volumes:
    - {MOUNT_SPECIFIER} 
"""

hooks.Filters.ENV_PATCHES.add_items(
    [
        (
            "openedx-dev-dockerfile-post-python-requirements",
            DOCKERFILE_PATCH_CONTENTS,
        ),
        (
            "local-docker-compose-dev-services",
            DOCKER_COMPOSE_PATCH_CONTENTS,
        ),
        (
            "dev-docker-compose-jobs-services",
            DOCKER_COMPOSE_JOBS_PATCH_CONTENTS,
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

