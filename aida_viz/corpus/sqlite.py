import sqlite3
from pathlib import Path
from typing import Iterable, Tuple

CORPUS_SCHEMA = """
    CREATE TABLE documents (
        parent_id text PRIMARY KEY,
        child_id text NOT NULL,
        lang_id text NOT NULL,
        fulltext text NOT NULL
    );
"""


def initialize_corpus(db_path: Path):
    """
    Initializes a "documents" SQL table at the provided database path.
    Erases existing "documents" table, if it exists.
    """
    with sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES) as connection:
        connection.execute("DROP TABLE IF EXISTS documents;")
        connection.execute(CORPUS_SCHEMA)


def insert_documents(db_path: Path, documents: Iterable[Tuple[str, str, str, str]]):
    with sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES) as connection:
        # TODO: replace this with an iterable over Document objects
        for parent, child, lang, fulltext in documents:
            _insert_document(connection, parent, child, lang, fulltext)


def _insert_document(
    connection: sqlite3.Connection,
    doc_id: str,
    child_id: str,
    lang_id: str,
    fulltext: str,
):
    sql = """
        INSERT INTO documents(parent_id, child_id, lang_id, fulltext)
        VALUES(?,?,?,?)
        """

    cur = connection.cursor()
    cur.execute(sql, (doc_id, child_id, lang_id, fulltext))
