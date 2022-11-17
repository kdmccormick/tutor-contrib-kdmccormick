import typing as t

import click
import subprocess
from tutor import hooks

tutor_root = ""

@hooks.Actions.PROJECT_ROOT_READY.add()
def _record_tutor_root(root: str):
    global tutor_root
    tutor_root = root



@click.command()
def configdiff():
    if not root:
        raise Exception
    script = f"""\
set -xeuo pipefail
rm -rf /tmp/tutor-configdiff
mkdir -p /tmp/tutor-configdiff
mv {tutor_root}/env /tmp/tutor-configdiff/env-save
tutor config save
diff {tutor_root}/env /tmp/tutor-configdiff/env-save
mv /tmp/tutor-configdiff/env-save {tutor_root}/env
"""
    subprocess.check_call(["echo", script])
    #subprocess.check_call(["bash", "-c", script])

hooks.Filters.CLI_COMMANDS.add_item(configdiff)
