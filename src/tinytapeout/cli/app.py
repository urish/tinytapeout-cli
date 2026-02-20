import click

from tinytapeout import __version__
from tinytapeout.cli.update_checker import check_for_updates


@click.group()
@click.version_option(version=__version__, prog_name="tt")
def cli():
    """Tiny Tapeout CLI - Design, test, and harden ASIC projects."""
    check_for_updates()


# Register commands
from tinytapeout.cli.commands.check import check  # noqa: E402
from tinytapeout.cli.commands.doctor import doctor  # noqa: E402
from tinytapeout.cli.commands.gds import gds  # noqa: E402

cli.add_command(doctor)
cli.add_command(check)
cli.add_command(gds)
