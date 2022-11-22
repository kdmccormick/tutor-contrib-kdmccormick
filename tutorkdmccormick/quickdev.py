"""
This plugin, which I'm calling "quickdev", is a proof-of-concept for
a set of changes that I think will simplify and speed up
the workflow for edx-platform developers using Tutor, particularly those
that need to quickly run edx-platform with modified requirement pins and/or
local package changes.

See this repository's README.rst for a full description of this plugin.
"""
from __future__ import annotations

import subprocess
import typing as t

import click
from tutor import hooks


@hooks.Filters.COMPOSE_MOUNTS.add()
def _mount_edx_platform_packages(
    volumes: list[tuple[str, str]], name: str
) -> list[tuple[str, str]]:
    """
    When a folder named xblock-* or platform-plugin-* is passed to --mount,
    auto-bind-mount it to lms* & cms* containers at /openedx/mounted-packages.

    (I chose xblock-* and platform-plugin-* because those are patterns I have seen.
     I also added platform-lib-* because it struck me as a sensible prefix for new
     edx-platform libraries. There are probably other patterns we could introduce as well.
     Many edx-platform packages are named "edx-*", but that seems too general of a pattern.)

    This allows us, in section (2) below, to automatically install all these
    mounted packages using a script. No private.txt file necessary!
    For example:

      tutor dev do    -m ./xblock-drag-and-drop-v2 pip-install-mounts
      tutor dev start -m ./xblock-drag-and-drop-v2

    Otherwise, the user needs to manually specify the location:

      tutor dev do \
        -m lms,...:./schoolyourself-xblock:/openedx/mounted-packages/schoolyourself-xblock \
        pip-install-mounts
      tutor dev start \
        -m lms,...:./schoolyourself-xblock:/openedx/mounted-packages/schoolyourself-xblock
    """
    if (
        name.startswith("xblock-")
        or name.startswith("platform-plugin-")
        or name.startswith("platform-lib-")
    ):
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


# USE NAMED VOLUMES FOR REQUIREMENTS
#
# Background:
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
# Here, we use named volumes for three things:
# * Python requirements (the virtualenv and the .egg-info file).
# * NPM requirements (node_modules).
# * Generated static assets (various edx-platform folders).
#
# This helps users because:
# * Changes to requirements & assets can be persisted and shared between
#   all lms* and cms* containers, _without_ having to
#   either rebuild the image (which takes time) or manage
#   mounted virtual environments (which is cumbersome and confusing).
# * Writing to any of these volumes is faster than writing either
#   directly to the container or to the bind-mounted edx-platform
#   directory.
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
# * These are all generated (that is, not git-managed) files,
#   with the minor exception of /openedx/edx-platform/lms/static/css,
#   which contains a git-managed 'vendor' folder. While it would be
#   best to move 'vendor' out of the volume so that edx-platform developers
#   can modify the folder and see their changes reflected, we are leaving
#   this as a TODO for now, since that folder hasn't been touched
#   in 7+ years and doesn't seem like something we should get hung
#   up on right now.
PYTHON_REQUIREMENT_VOLUMES: dict[str, str] = {
    "openedx_venv": "/openedx/venv",
    "openedx_egg_info": "/openedx/edx-platform/Open_edX.egg-info",
}
NODE_REQUIREMENT_VOLUMES: dict[str, str] = {
    "openedx_node_modules": "/openedx/edx-platform/node_modules",
}
STATIC_ASSET_VOLUMES: dict[str, str] = {
    # Yeah, there are seven different edx-platform directories
    # for generated static assets. Gross. It's be nice to
    # work upstream to simplify this.
    "openedx_common_static_bundles": "/openedx/edx-platform/common/static/bundles",
    "openedx_common_static_common_css": "/openedx/edx-platform/common/static/common/css",
    "openedx_common_static_common_js_vendor": (
        "/openedx/edx-platform/common/static/common/js/vendor"
    ),
    "openedx_common_static_xmodule": "/openedx/edx-platform/common/static/xmodule",
    "openedx_lms_static_certificates_css": "/openedx/edx-platform/lms/static/certificates/css",
    # note: /openedx/edx-platform/lms/static/css/vendor is git-managed,
    #       unlike all the other directories here. The folder hasn't changed
    #       in git in 7+ years, so I'm not too concerned about the
    #       fact that it's getting sucked into the named volume.
    "openedx_lms_static_css": "/openedx/edx-platform/lms/static/css",
    "openedx_cms_static_css": "/openedx/edx-platform/cms/static/css",
}
ALL_NAMED_VOLUMES: dict[str, str] = {
    **PYTHON_REQUIREMENT_VOLUMES,
    **NODE_REQUIREMENT_VOLUMES,
    **STATIC_ASSET_VOLUMES,
}

# Add volumes to 'development' stage of Dockerfile.
DOCKERFILE_PATCH: str = "\n".join(
    [
        "##### BEGIN QUICKDEV PATCH #####",
        "RUN mkdir -p /openedx/mounted-packages",  # For auto-bind-mounted platform packages.
        *[
            # Declare each volume mount point.
            # Docker will expect a volume to be associated with each of these
            # via the docker-compose file.
            # If the associated volume is empty, then upon startup, the
            # volume will be populated with the original contents of the same
            # directory from the image.
            f"VOLUME {container_path}"
            for _volume_name, container_path in ALL_NAMED_VOLUMES.items()
        ],
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
    compose_file: dict, volumes: dict[str, str], service_names: list[str]
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


@click.command()
@click.option(
    "-s",
    "--build-static",
    is_flag=True,
    default=False,
    show_default=True,
    help="Rebuild static assets after installing packages",
)
def pip_install_mounts(build_static: bool) -> list[tuple[str, str]]:
    """
    Install all from /openedx/mounted-packages.
    """
    script = """
set -eu  # Stricter mode

if [ -z "$(ls /openedx/mounted-packages 2>/dev/null)" ] ; then
	echo "Directory /openedx/mounted-packages is empty; nothing to install." >&2
        exit 0
fi

echo "Installing packages from /openedx/mounted-packages..." >&2
set -x
for PACKAGE in /openedx/mounted-packages/* ; do
        pip install -e "$PACKAGE"
done
set +x
echo "Done installing packages from /openedx/mounted-packages." >&2
"""
    if build_static:
        script += "set -x\nopenedx-assets build --env=dev\n"
    return [("lms", script)]


hooks.Filters.CLI_DO_COMMANDS.add_item(pip_install_mounts)


@click.group()
def quickdev():
    """
    Extra 'dev' commands for managing named volumes
    """


hooks.Filters.CLI_COMMANDS.add_item(quickdev)


@quickdev.command()
def pip_restore() -> None:
    """
    Revert to original Python requirements from Docker image.
    """
    _delete_volumes(PYTHON_REQUIREMENT_VOLUMES.keys())


@quickdev.command()
def npm_restore() -> None:
    """
    Revert to original Node packages from Docker image.
    """
    _delete_volumes(NODE_REQUIREMENT_VOLUMES.keys())


@quickdev.command()
def static_restore() -> None:
    """
    Revert to original built assets from the Docker image.
    """
    _delete_volumes(STATIC_ASSET_VOLUMES.keys())


@quickdev.command(
    name="pip-install-mounts",
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
def _pip_install_mounts_old() -> None:
    """
    Deprecated - use 'tutor dev do pip-install-mounts'.
    """
    raise click.ClickException(
        """\
'tutor quickdev pip-install-mounts -m/--mount ...' is deprecated.

Instead, use the equivalent do-job, like this:

  tutor dev do --mount=/some/package --mount=/another/package pip-install-mounts

or this:

  tutor dev do -m /some/package -m /another/package pip-install-mounts"""
    )


def _delete_volumes(volume_names: t.Iterable[str]) -> None:
    """
    Stop containers & delete one or more named `tutor dev` volumes.
    """
    import tutor.__about__ as tutor_about  # pylint: disable=import-outside-toplevel

    # Bring down all `tutor dev` containers so that we can delete volumes.
    # We must use `down` instead of `stop`, because the latter doesn't bring
    # down `tutor dev run` containers. Note that `down` also will prune all
    # stopped containers for us.
    subprocess.check_call(["tutor", "dev", "dc", "down"])

    # I don't know of a way to delete specific volumes through docker-compose,
    # so we must hackily build the volume names ourselves based on the compose
    # project name.
    compose_project = tutor_about.__app__.replace("-", "_") + "_dev"
    volume_names = [f"{compose_project}_{volume_name}" for volume_name in volume_names]
    subprocess.check_call(["docker", "volume", "rm", *volume_names])


# @hooks.Actions.IMAGE_BUILT.add()
# @hooks.Filters.IMAGE_PULLED.add()
def _handle_image_change(image: str) -> None:
    """
    HYPOTHETICAL: Delete requirement & asset volumes whenever image changes.

    The IMAGE_BUILT and IMAGE_PULLED actions do not exist in Tutor (yet),
    but if they did, we could hook into them in order to smartly delete
    the named volumes holding our Python virtualenv, node_modules, and generated
    static assets.

    Why?

    If we never delete these volumes, then users will need to remember
    to regularly either (a) upate requirements and static assets, or (b) delete
    the named volumes manually using the `*-restore` commands defined above.
    Many users may find this cumbersome, since they already need to remember
    to tutor-pull new images and git-pull edx-platform regularly.

    So, we should delete the named volumes in an automatic yet also
    predictable fashion. `tutor images pull/build opnedx` strikes me as a good
    time to trigger the volume removal, since folks tend to run it when
    they want a fresh, updated environment.
    """
    if image == "openedx":
        _delete_volumes(ALL_NAMED_VOLUMES.keys())
