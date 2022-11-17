import typing as t

import click
import subprocess
from tutor import hooks


@hooks.Actions.PROJECT_ROOT_READY.add()
def _record_tutor_root(root: str):

    @click.command()
    def configdiff():
        script = f"""\
set -euo pipefail
rm -rf /tmp/tutor-configdiff
mkdir -p /tmp/tutor-configdiff
cd /tmp/tutor-configdiff
mv {root}/env ./CURRENT_ENV
tutor config save 1>/dev/null
mv {root}/env ./NEW_ENV
diff CURRENT_ENV NEW_ENV && echo "Your Tutor environment is up to date." || true
mv ./CURRENT_ENV {root}/env
"""
        subprocess.check_call(["echo", script])
        subprocess.check_call(["bash", "-c", script])


    hooks.Filters.CLI_COMMANDS.add_item(configdiff)
