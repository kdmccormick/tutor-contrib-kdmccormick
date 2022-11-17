import typing as t

import click
import subprocess
from tutor import hooks


@hooks.Actions.PROJECT_ROOT_READY.add()
def _record_tutor_root(root: str):

    @click.command()
    def configdiff():
        script = f"""\
set -xeuo pipefail
rm -rf /tmp/tutor-configdiff
mkdir -p /tmp/tutor-configdiff
mv {root}/env /tmp/tutor-configdiff/env-save
tutor config save
diff {root}/env /tmp/tutor-configdiff/env-save
mv /tmp/tutor-configdiff/env-save {root}/env
"""
        #subprocess.check_call(["echo", script])
        subprocess.check_call(["bash", "-c", script])


    hooks.Filters.CLI_COMMANDS.add_item(configdiff)
