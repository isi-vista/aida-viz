import argparse
import sqlite3
from pathlib import Path
from zipfile import ZipFile

from .corpus import get_text_docs
from .database import create_schema, insert_document

USAGE = """
    Creates an SQLite database file from the AIDA Phase 1 Evaluation Source Data in .zip format.
    (Note that LDC distributes this data in .tgz format. You must first convert it to .zip.)
"""


def getargs():
    """Get command-line arguments."""
    parser = argparse.ArgumentParser(usage=USAGE)
    arg = parser.add_argument

    arg(
        "-z",
        "--zip",
        type=ZipFile,
        help=".zip file containing the LDC corpus (LDC)",
        required=True,
    )

    arg(
        "-d",
        "--db",
        type=Path,
        help="Write location for the database file.",
        required=True,
    )

    return parser.parse_args()


def main():
    args = getargs()
    corpus, db = args.zip, args.db

    docs = get_text_docs(corpus)

    if not db.exists():
        db.touch()
        new = True

    conn = sqlite3.connect(str(db), detect_types=sqlite3.PARSE_DECLTYPES)

    if new:
        with conn:
            create_schema(conn)

    with conn:
        for doc_id, fulltext in docs.items():
            insert_document(conn, doc_id, fulltext)

    print(f"Database created at {db}")


main()
