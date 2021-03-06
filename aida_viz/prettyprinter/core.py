from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from immutablecollections import immutabledict
from jinja2 import Template
from rdflib import RDF, URIRef
from rdflib.namespace import split_uri

from aida_viz.corpus.core import Corpus
from aida_viz.documents import get_title_sentence, render_single_justification_document
from aida_viz.elements import Element, Justification, Statement

class PrettyPrinter:
    corpus: Corpus
    elements: Dict[URIRef, Element]

    def __init__(
        self,
	corpus: Corpus,
        elements: Dict[URIRef, Element],
        directory="./aida-viz-text",
    ):
        self.corpus = corpus
        self.elements = elements
        self.parent_child_map = {
            r["child_id"]: r["parent_id"]
            for r in self.corpus.query(f"SELECT parent_id, child_id FROM documents")
        }
        self.output_dir: Path = directory

    def write_to_dir(self, output_file_name: str = "pretty-print.txt"):
        if self.output_dir.exists() and not self.output_dir.is_dir():
            raise ValueError("argument `output_dir` must be directory.")

        text_file = self.output_dir / output_file_name
        text_lines = ["element_type\telement_id\tstatements\tjustifications\tprototypes\tmembers\tclusters\tnames\thandles\tjustification_details"]

        element_list_by_type = defaultdict(list)
        for element in self.elements.values():
            if element.element_type and "#" in element.element_type:
                _, element_type = split_uri(element.element_type)
            else:
                element_type = element.element_type
            element_list_by_type[element_type].append(element)

        for element_type, element_list in element_list_by_type.items():
            for element in sorted(element_list, key=lambda e: e.element_id):
                rendered_element_text = self.render_element(element)
                text_lines.append(rendered_element_text)

        rendered_text = "\n".join(text_lines)
        text_file.write_text(rendered_text)

    def render_element(self, element: Element) -> str:
        text_line = ""
        statements = ""
        if element.element_type and "#" in element.element_type:
            _, element_type = split_uri(element.element_type)
        else:
            element_type = element.element_type

        if "#" in element.element_id:
            _, element_id = split_uri(element.element_id)
        else:
            element_id = element.element_id

        justifications = element.informative_justifications + element.justified_by
        text_line = f"{self.render_justifications(justifications)}\t{element.prototypes}\t{element.members}\t{element.clusters}\t{element.names}\t{element.handles}\t{justifications}"

        if element.statements:
            statements = self.render_statements(element.statements) 

        return f"{element_type}\t{element.element_id}\t{statements}\t{text_line}"


    def render_justifications(self, justifications: List[Justification]) -> str:
        """Returns spanning text for a comma-separated list of justification links"""

        rendered_justifications = set()
        for j in justifications:
            document_id = (
                j.parent_id if j.parent_id else self.parent_child_map[j.child_id]
            )
            if j.span_start and j.span_end:
                spanning_tokens = self.corpus[document_id]["fulltext"][
                    j.span_start : j.span_end + 1
                ]
                rendered_justifications.update([spanning_tokens])
#                self.write_justification_context_html(j)

        return ", ".join(rendered_justifications)

    def render_statements(self, statements: List[Statement]) -> str:
        text_lines = []

        type_statements = [s for s in statements if s.predicate == RDF.type]
        nontype_statements = [s for s in statements if s.predicate != RDF.type]
        type_prefix = None

        if type_statements:
            type_statement = type_statements[0]
            _, type_prefix = split_uri(type_statement.object)
            text_lines.append(f"{self._render_statement(type_statement)}")

        for statement in nontype_statements:
            text_lines.append(
                f"{self._render_statement(statement, type_prefix=type_prefix)}"
            )

        return ";; ".join(text_lines)

    def _render_statement(
        self, statement: Statement, type_prefix: Optional[str] = None
    ) -> str:
        _, pred = split_uri(statement.predicate)

        if type_prefix:
            pred = pred.replace(type_prefix, "")

        return f"{pred}: {self.anchor_link(statement.object)} (Justified by {self.render_justifications(statement.justified_by)})"

    def anchor_link(self, element_id: URIRef) -> str:
        _, suffix = split_uri(element_id)
        return (
            f"{element_id} {suffix}"
            if element_id in self.elements
            else suffix
        )
