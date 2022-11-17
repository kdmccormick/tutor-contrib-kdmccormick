"""
Implementation of the configdiff mini-plugin. See README for documentation.
"""
import os
from subprocess import run, CalledProcessError, PIPE, STDOUT
from pathlib import Path

import click
from tutor import hooks


@hooks.Actions.PROJECT_ROOT_READY.add()
def _record_tutor_root(root: str):
    @click.command()
    def configdiff():
        compare_root = Path("/", "tmp", "tutor-contrib-kdmccormick", "configdiff")
        actual_root = Path(root)
        before = Path("BEFORE")
        after = Path("AFTER")
        run(["rm", "-rf", compare_root], check=True)
        run(["mkdir", "-p", compare_root / after], check=True)
        run(["mkdir", "-p", compare_root / before], check=True)
        run(
            [
                "cp",
                "-r",
                actual_root / "config.yml",
                actual_root / "env",
                compare_root / before,
            ],
            check=True,
        )
        run(
            [
                "cp",
                "-r",
                actual_root / "config.yml",
                actual_root / "env",
                compare_root / after,
            ],
            check=True,
        )

        try:
            run(
                ["tutor", "config", "save"],
                env={**os.environ, "TUTOR_ROOT": compare_root / after},
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
            )
        except CalledProcessError as exc:
            click.echo(
                "------------------------------------------------------------", err=True
            )
            click.echo(exc.output.decode("utf-8"), err=True)
            click.echo(
                "------------------------------------------------------------", err=True
            )
            raise click.ClickException(
                "Failed to run `tutor config save. Output is captured above."
            )  # pylint: disable=raise-missing-from
        try:
            run(
                ["diff", before / "env", after / "env"],
                cwd=str(compare_root),
                check=True,
            )
        except CalledProcessError as exc:
            # When diff exits 1, it just means that there was a difference.
            # The output will have been printed to the console.
            # Otherwise, any other return code implies that an error occurred.
            if exc.returncode != 1:
                raise
        else:
            # When diff exits 0, it means there was no difference.
            click.echo("Your Tutor environment is up to date.", err=True)

    hooks.Filters.CLI_COMMANDS.add_item(configdiff)
