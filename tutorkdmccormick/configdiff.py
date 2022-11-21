import typing as t
from subprocess import check_call
from pathlib import PurePath

import click
from tutor import hooks


@hooks.Actions.PROJECT_ROOT_READY.add()
def _record_tutor_root(root: str):

    @click.command()
    def configdiff():
        tmp_area = PurePath("/") / 'tmp' / 'tutor' / 'configdiff'
        compare_root = tmp_area
        actual_root = PurePath(root)
        before = PurePath('BEFORE')
        after = PurePath('AFTER')
        script = f"""\
set -euo pipefail
rm -rf '{tmp_area}'
mkdir -p '{tmp_area / after}'
ln -s '{actual_root}' '{tmp_area / before}'
cp '{actual_root / "config.yml"}' '{tmp_area / after}'
TUTOR_ROOT='{tmp_area / after}' tutor config save 1>/dev/null
cd {tmp_area}
diff '{before}/env' '{after}/env' && echo "Your Tutor environment is up to date." || true
"""
        check_call(["rm", "-rf", compare_root])
        check_call(["mkdir", "-p", compare_root / after])
        check_call(["ln", "-s", actual_root, compare_root / before])
        check_call(["bash", "-c", f"TUTOR_ROOT='{tmp_area / after}' tutor config save 1>/dev/null"])
        check_call(["bash", "-c", f"cd '{tmp_area}' && diff '{before}' '{after}'"])

        #check_call(["bash", "-c", script])

    hooks.Filters.CLI_COMMANDS.add_item(configdiff)
