"""
This plugin, which I'm calling "quickdev", is a proof-of-concept for
a set of four improvements that I think will simplify and speed up
the workflow for edx-platform developers using Tutor, particularly those
that need to quickly run edx-platform with modified requirement pins and/or
local package changes.

The improvements are described in more detail below:
  1.  AUTO-MOUNT PACKAGES TO A STANDARD LOCATION
  2.  ADD A SCRIPT TO PREPARE A MOUNTED PLATFORM
  3.  USE NAMED VOLUMES FOR REQUIREMENTS
  4a. ALLOW REQUIREMENT VOLUMES TO BE DELETED VIA COMMAND
  4b. DELETE REQUIREMENT VOLUMES ON IMAGE CHANGE
"""
import click
import pkg_resources
import subprocess
import typing as t

from tutor import hooks


##########################################################################
# 1. AUTO-MOUNT PACKAGES TO A STANDARD LOCATION
#
# We choose a standard location for mounting edx-platform packages
# in development: /openedx/mounted-packages.
# This allows us, in section (2) below, to automatically install all these
# mounted packages using a script. No private.txt file necessary!
#
# If the package name begins with xblock-* or platform-plugin-*,
# then we can mount it there automatically:
#
#   tutor dev run -m ./xblock-adventure ...
#
# Otherwise, the user needs to manually specify the location:
#
#   tutor dev run -m \
#     lms,...:./schoolyourself-xblock:/openedx/mounted-packages/schoolyourself-xblock ...
#
##########################################################################


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


##########################################################################
# 2. ADD A SCRIPT TO PREPARE A MOUNTED edx-platform
#
# Currently, if a user mounts edx-platform, they must run several follow-up
# commands in order for their code to run correctly:
#   https://docs.tutor.overhang.io/dev.html#setting-up-a-development-environment-for-edx-platform
#
# And, if the user wants to install locally-modified edx-platform packages,
# there are additional steps.
#
# We propose a script that would simplify this into one command:
#
#     tutor dev run -m path/to/edx-platform lms \
#       bash /openedx/quickdev/bin/prepare-mounted-platform
#
# If this plugin were moved into core, then the script could be put at
# /openedx/bin/prepare-mounted-platform and then run as simply:
#
#    tutor dev run -m path/to/edx-platform lms prepare-mounted-platform
##########################################################################

# Render any templates within tutorkdmccormick/templates/quickdev to plugins/quickdev.
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    pkg_resources.resource_filename("tutorkdmccormick", "templates")
)
hooks.Filters.ENV_TEMPLATE_TARGETS.add_item(("quickdev", "plugins"))


##########################################################################
# 3. USE NAMED VOLUMES FOR REQUIREMENTS
#
# A "named volume" is a type of Docker volume. It's similar to bind-mount
# volumes, except that we cannot access its contents easily via the host
# filesystem. The contents are stored in a Docker-internal fashion, and
# the volume itself is referred by an identifier that we provide in
# the docker-compose YAML file. They are ideal for situations where
# containers need to read and write shared data, but the host doesn't
# need to modify the data. For writing, they outperform the
# layered container filesystem significantly, and on macOS and Windows
# they also outperform bind-mounts.
#
# We use named volumes here to store requirements because we want users
# to be able to install modified requirements (both Python and NPM ones),
# using `docker run`, such that the changes will be reflected in
# containers. In the past I've tried doing this by bind-mounting
# virtual environments into containers, but this is quite cumbersome
# and, on macOS, quite slow. Named volumes seems to solve both these
# problems.
##########################################################################

DOCKERFILE_PATCH_CONTENTS = """\
## BEGIN QUICKDEV PATCH

# Make a place for in-devlopment edx-platform packages to be mounted to
# and installed from.
VOLUME /openedx/mounted-packages

# Turn the Python venv, node_modules, static assets, and .egg-info
# into named volumes so that:
# (a) they can be written to faster in the event that the
#     user wants to re-install requirements and/or rebuild assets,
#     since named volumes have better write performance than both
#     container filesystems and bind-mounted volumes; and
# (b) they can be shared between all lms* and cms* containers.
#
# Notes:
# * These declarations are volume "placeholders".
#   They are associated with actual named volumes via
#   Tutor's docker-compose YAML files (which we patch below).
# * When a container is started: if the assigned named
#   volume exists, then it will be used; if not, a new
#   volume will be created and pre-populated with the original
#   contents of this directory from the image. This is extremely
#   useful for us, because it means that the volumes by-default
#   have the requirements that are built into the dev image!
# * Yes, the volumes within /openedx/edx-platform/
#   will point at their named volumes, *even if* a user bind-mounts
#   their own repository to /openedx/edx-platform! The volumes
#   just seem to be layered on top of one another so that in
#   any given folder, the most specific volume "wins".
#   TODO: I tested this on Linux; need to verify this behavior on macOS.
VOLUME /openedx/venv
VOLUME /openedx/edx-platform/node_modules
VOLUME /openedx/edx-platform/common/static
VOLUME /openedx/edx-platform/Open_edX.egg-info

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

# Declare these all as named volumes.
DEV_REQUIREMENT_VOLUMES: t.Dict[str, dict] = {
    "openedx_venv": {},
    "openedx_node_modules": {},
    "openedx_static": {},
    "openedx_egg_info": {},
}

# Associate the named volumes with their corresponding
# container filesystem locations, as declared in the
# Dockerfile patch above.
NEW_SERVICE_VOLUME_MAPPINGS: t.List[str] = [
    "openedx_venv:/openedx/venv",
    "openedx_node_modules:/openedx/edx-platform/node_modules",
    "openedx_static:/openedx/edx-platform/common/static",
    "openedx_egg_info:/openedx/edx-platform/Open_edX.egg-info",
]

# Bind-mount this plugin's scripts at /openedx/quickdev/bin.
NEW_SERVICE_VOLUME_MAPPINGS.append(
    "../plugins/quickdev/bin:/openedx/quickdev/bin:ro",
)


@hooks.Filters.COMPOSE_DEV_TMP.add()
def _add_volumes_to_openedx_services(docker_compose_tmp: dict) -> dict:
    return _add_volumes_to_services(
        docker_compose_tmp, ["lms", "cms", "lms-worker", "cms-worker"]
    )


@hooks.Filters.COMPOSE_DEV_JOBS_TMP.add()
def _add_volumes_to_openedx_jobs_services(docker_compose_tmp: dict) -> dict:
    return _add_volumes_to_services(docker_compose_tmp, ["lms-job", "cms-job"])


def _add_volumes_to_services(compose_file: dict, service_names: t.List[str]) -> dict:
    """
    Given a compose file, return a new compose file where our new volumes
    are declared and added to the specified services.
    """
    services = compose_file.get("services", {})
    return {
        **compose_file,
        "volumes": {
            **compose_file.get("volumes", {}),
            **DEV_REQUIREMENT_VOLUMES,
        },
        "services": {
            **compose_file.get("services", {}),
            **{
                service_name: {
                    **services.get(service_name, {}),
                    "volumes": [
                        *services.get(service_name, {}).get("volumes", []),
                        *NEW_SERVICE_VOLUME_MAPPINGS,
                    ],
                }
                for service_name in service_names
            },
        },
    }
    return compose_file


##########################################################################
# 4a. ALLOW REQUIREMENT VOLUMES TO BE DELETED VIA COMMAND
#
# Users will sometimes want to "restore" the requirements that are provided
# by the openedx image. This command would allow them to do that:
#
#  tutor restore-dev-requirements
#
# For what it's worth: I think this is clunky and unreliable. I don't think
# this should be introduced to the core. I would rather implement
# idea 4b (below).
##########################################################################


@hooks.Filters.CLI_COMMANDS.add_item
@click.command()
def restore_dev_requirements():
    _delete_dev_requirement_volumes()


def _delete_dev_requirement_volumes():
    """
    Delete the volumes holding the Python venv and the NPM modules for development mode.

    TODO: I would love to find a less hacky & more reliable way to implement this.
    """
    import tutor.__about__ as tutor_about

    compose_project = tutor_about.__app__.replace("-", "_") + "_dev"
    volume_names = [
        f"{compose_project}_{volume}" for volume, _ in DEV_REQUIREMENT_VOLUMES.items()
    ]
    # Stop containers and remove them so that we can delete these volumes.
    # TODO: This will fail if any `tutor dev run` containers are running
    # because `tutor dev stop` doesn't kill those.
    subprocess.Popen(["tutor", "dev", "stop"]).wait()
    subprocess.Popen(["tutor", "dev", "dc", "rm", "-f"]).wait()
    subprocess.Popen(["docker", "volume", "rm", *volume_names]).wait()


##########################################################################
# 4b. DELETE REQUIREMENT VOLUMES ON IMAGE CHANGE
#     (this doesn't work yet)
#
# The IMAGE_BUILT and IMAGE_PULLED actions do not exist in Tutor (yet),
# but if they did, we could hook into them in order to smartly delete
# the virtualenv and node_modules volumes. That way, users would be
# less likely to accidentally use outdated requirements from the volumes
# after they pulled/built a fresh image.
#
# I believe that this would cover almost all of the cases where users
# would want to delete the requirements volumes, so if we could get
# it working, then we could get rid of the command proposed
# in idea 4a (above).
##########################################################################

# @hooks.Actions.IMAGE_BUILT.add()
# @hooks.Filters.IMAGE_PULLED.add()
def _handle_image_change(image: str) -> None:
    if image == "openedx":
        _delete_dev_requirement_volumes()
