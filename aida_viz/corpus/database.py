import sqlite3
from pathlib import Path

from immutablecollections import ImmutableDict, immutabledict


def get_db(db_path: Path) -> sqlite3.Connection:
    ta1_db = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)

    # this line causes database queries to output Row objects (instead of tuples).
    # Data in a Row object can be accessed by keyword, like a dict.
    ta1_db.row_factory = sqlite3.Row

    return ta1_db


def document_entry(db_path: Path, document_id: str) -> ImmutableDict[str, str]:
    with get_db(db_path) as db:
        document = db.execute(
            "SELECT document_id, fulltext"
            " FROM documents"
            f' WHERE document_id=="{document_id}"'
        ).fetchone()

    return immutabledict(document)


def create_schema(connection: sqlite3.Connection):
    sql = """
        CREATE TABLE documents (
            document_id text PRIMARY KEY,
            fulltext text NOT NULL
            );
        """

    cur = connection.cursor()
    cur.execute(sql)

    print("Created Schema")


def insert_document(connection: sqlite3.Connection, doc_id: str, fulltext: str):
    sql = """
        INSERT INTO documents(document_id, fulltext)
        VALUES(?,?)
        """

    cur = connection.cursor()
    cur.execute(sql, (doc_id, fulltext))
