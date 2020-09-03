from pathlib import Path
from typing import Optional
from zipfile import ZipFile

import click

from . import core


@click.group()
def cli():
    pass


@cli.command(
    help="""
        Creates an SQLite database file from the AIDA Phase 1 Evaluation Source Data in .zip format.
        (Note that LDC distributes this data in .tgz format. You must first convert it to .zip.)
    """
)
@click.option(
    "-z",
    "--ldc_zip",
    type=ZipFile,
    help=".zip file containing the LDC corpus (LDC)",
    required=True,
)
@click.option(
    "-w",
    "--write_to",
    type=Path,
    help="Write location for the new database file.",
    required=True,
)
@click.option(
    "--prefix",
    type=str,
    help="Write location for the new database file.",
    required=False,
)
def build_corpus(ldc_zip: ZipFile, write_to: Path, prefix: Optional[str]):
    core.build_sqlite(ldc_zip, write_to, prefix=prefix)


if __name__ == "__main__":
    cli()
