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
_TODO = """
    * update comments
    * move commands under quickdev:
      * tutor qdev pip-install-mounted
      * tutor qdev pip-restore
      * tutor qdev npm-restore
      * tutor qdev static-restore
      * tutor qdev ....rest of dev commands
    * figure out why mounted block demo didnt work
    * delete mounted platform script
    * test on a mac
    * document the plugin
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
#
# (comments previously in dockerfile)
#
# Turn the Python venv, node_modules, .egg-info, and generated
# static assets into named volumes so that:
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
# * These are all generated (that is, not git-managed) files,
#   with the minor exception of /openedx/edx-platform/lms/static/css,
#   which contains a git-managed 'vendor' folder. While it would be
#   best to move 'vendor' out of the volume so that edx-platform developers
#   can modify the folder and see their changes reflected, we are leaving
#   this as a TODO for now, since that folder hasn't been touched
#   in 7+ years and doesn't seem like something we should get hung
#   up on right now.
##########################################################################

"""
TODO: scripts?

"../plugins/quickdev/bin:/openedx/quickdev/bin:ro"

# Make a place for in-devlopment edx-platform packages to be mounted to
# and installed from.
VOLUME /openedx/mounted-packages
"""


PYTHON_REQUIREMENT_VOLUMES: t.Dict[str, str] = {
    "openedx_venv": "/openedx/venv",
    "openedx_egg_info": "/openedx/edx-platform/Open_edX.egg-info",
}
NODE_REQUIREMENT_VOLUMES: t.Dict[str, str] = {
    "openedx_node_modules": "/openedx/edx-platform/node_modules",
}
STATIC_ASSET_VOLUMES: t.Dict[str, str] = {
    "openedx_common_static_bundles": "/openedx/edx-platform/common/static/bundles",
    "openedx_common_static_common_css": "/openedx/edx-platform/common/static/common/css",
    "openedx_common_static_common_js_vendor": "/openedx/edx-platform/common/static/common/js/vendor",
    "openedx_common_static_xmodule": "/openedx/edx-platform/common/static/xmodule",
    "openedx_lms_static_certificates_css": "/openedx/edx-platform/lms/static/certificates/css",
    "openedx_lms_static_css": "/openedx/edx-platform/lms/static/css",
    "openedx_cms_static_css": "/openedx/edx-platform/cms/static/css",
}
ALL_NAMED_VOLUMES: t.Dict[str, str] = {
    **PYTHON_REQUIREMENT_VOLUMES,
    **NODE_REQUIREMENT_VOLUMES,
    **STATIC_ASSET_VOLUMES,
}


DOCKERFILE_PATCH: str = "\n".join(
    [
        "##### BEGIN QUICKDEV PATCH #####",
        "",
        "# Mount point for auto-bind-mounted edx-platform packages",
        "RUN mkdir -p /openedx/mounted-packages",
        "",
        "# Named volumes for Python & NPM requirements as well as generated",
        "# static assets.",
        *[
            f"VOLUME {container_path}"
            for _volume_name, container_path in ALL_NAMED_VOLUMES.items()
        ],
        "",
        "#####  END QUICKDEV PATCH  #####",
    ]
)
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-dev-dockerfile-post-python-requirements",
        DOCKERFILE_PATCH,
    ),
)


@hooks.Filters.COMPOSE_DEV_TMP.add()
def _add_volumes_to_openedx_services(docker_compose_tmp: dict) -> dict:
    return _add_volumes_to_services(
        docker_compose_tmp,
        ALL_NAMED_VOLUMES,
        ["lms", "cms", "lms-worker", "cms-worker"],
    )


@hooks.Filters.COMPOSE_DEV_JOBS_TMP.add()
def _add_volumes_to_openedx_jobs_services(docker_compose_tmp: dict) -> dict:
    return _add_volumes_to_services(
        docker_compose_tmp, ALL_NAMED_VOLUMES, ["lms-job", "cms-job"]
    )


def _add_volumes_to_services(
    compose_file: dict, volumes: t.Dict[str, str], service_names: t.List[str]
) -> dict:
    """
    Add named volumes to certain services in a docker-compose file.
    """
    services = compose_file.get("services", {})
    return {
        **compose_file,
        # Add declarations for named volumes.
        # We map each volume name to '{}' to indicate that's a basic named volume.
        "volumes": {
            **compose_file.get("volumes", {}),
            **{volume_name: {} for volume_name, _ in volumes.items()},
        },
        # App volume->directory mappings for each named volume for service.
        # Each mapping is a string in the form "$VOLUME_NAME:$CONTAINER_PATH".
        "services": {
            **compose_file.get("services", {}),
            **{
                service_name: {
                    **services.get(service_name, {}),
                    "volumes": [
                        *services.get(service_name, {}).get("volumes", []),
                        *[
                            f"{volume_name}:{container_path}"
                            for volume_name, container_path in volumes.items()
                        ],
                    ],
                }
                for service_name in service_names
            },
        },
    }


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


@click.group(help="Extra 'dev' commands for working with named volumes")
def quickdev():
    pass


hooks.Filters.CLI_COMMANDS.add_item(quickdev)


@quickdev.command(help="TODO...")
def pip_install_mounted():
    script = """
set -euo pipefail  # Strict mode

if [ -n "$(ls /openedx/mounted-packages)" ] ; then
	echo "Installing packages from /openedx/mounted-packages..." >&2
	set -x
	for PACKAGE in /openedx/mounted-packages/* ; do
		pip install -e "$PACKAGE"
	done
	set +x
	echo "Done installing packages from /openedx/mounted-packages." >&2
else
	echo "Directory /openedx/mounted-packages is empty; nothing to install." >&2
fi
"""
    command = ["tutor", "dev", "exec", "lms", "bash", "-c", script]
    try:
        subprocess.check_call(command)
    except:
        print("Hint: did you forget start LMS before running pip-install-mounted?")
        raise


@quickdev.command(help="Revert to original Python requirements from Docker image")
def pip_restore():
    _delete_volumes(PYTHON_REQUIREMENT_VOLUMES.keys())


@quickdev.command(help="Revert to original Node packages from Docker image")
def npm_restore():
    _delete_volumes(NODE_REQUIREMENT_VOLUMES.keys())


@quickdev.command(help="Revert to original built assets from the Docker image")
def static_restore():
    _delete_volumes(STATIC_ASSET_VOLUMES.keys())


def _delete_volumes(volume_names: t.List[str]):
    """
    Delete one or more volumes being used by `tutor dev`.

    TODO: I would love to find a less hacky & more reliable way to implement this.
    """
    import tutor.__about__ as tutor_about

    # TODO: This is a pretty gross way of figuring out the volumes names.
    compose_project = tutor_about.__app__.replace("-", "_") + "_dev"
    volume_names = [f"{compose_project}_{volume_name}" for volume_name in volume_names]

    subprocess.check_call(["tutor", "dev", "dc", "down"])
    subprocess.check_call(["docker", "volume", "rm", *volume_names])


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
        _delete_volumes(ALL_NAMED_VOLUMES.keys())
