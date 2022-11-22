"""
A Tutor plugin to automatically stop Nightly containers when starting
Stable containers, and vice versa.

Implementation is currently hacky.
"""
from __future__ import annotations

from tutor import hooks

# isort:skip
# HACK: None of these modules are part of the official plugin API.
from tutor import config as tutor_config
from tutor.__about__ import __app__ as tutor_current_app
from tutor.commands.dev import DevTaskRunner
from tutor.commands.local import LocalTaskRunner


@hooks.Actions.COMPOSE_PROJECT_STARTED.add()
def _stop_other_projects(root: str, config: dict, project_name: str) -> None:
    """
    When Tutor Stable is started, stop Nightly (both dev and local modes).
    When Tutor Nightly is started, stop Stable (both dev and local modes).

    Tutor Stable already takes care of stopping dev mode when local is started,
    and vice versa. Same thing for Tutor Nightly. It's just across Stable<->Nightly
    that doesn't get automatically stopped without this function.
    """
    # Ignore the provided config and project, because it's not what we want
    # to stop.
    _ = config
    _ = project_name

    app_to_stop = "tutor" if tutor_current_app == "tutor-nightly" else "tutor-nightly"
    app_to_stop = app_to_stop.replace("-", "_")

    with hooks.contexts.enter("stop-other-projects"):

        @hooks.Filters.ENV_TEMPLATE_VARIABLES.add()
        def _replace_tutor_app(template_vars):
            template_vars_without_tutor_app = [
                (name, value) for name, value in template_vars if name != "TUTOR_APP"
            ]
            return template_vars_without_tutor_app + [("TUTOR_APP", app_to_stop)]

    config_to_stop = tutor_config.load(root)
    hooks.clear_all(context="stop-other-projects")

    LocalTaskRunner(root, config_to_stop).docker_compose("stop")
    DevTaskRunner(root, config_to_stop).docker_compose("stop")
