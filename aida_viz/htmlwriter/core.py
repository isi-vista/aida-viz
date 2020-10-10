from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from immutablecollections import immutabledict
from jinja2 import Template
from rdflib import RDF, URIRef
from rdflib.namespace import split_uri
from tqdm import tqdm

from aida_viz.corpus.core import Corpus
from aida_viz.documents import get_title_sentence, render_single_justification_document
from aida_viz.elements import Element, Justification, Statement
from aida_viz.htmlwriter.resources import STYLE, TEMPLATE


class HtmlWriter:
    corpus: Corpus
    elements: Dict[URIRef, Element]

    def __init__(self, corpus: Corpus, elements: Dict[URIRef, Element]):
        self.corpus = corpus
        self.elements = elements
        self.parent_child_map = {
            r["child_id"]: r["parent_id"]
            for r in self.corpus.query(f"SELECT parent_id, child_id FROM documents")
        }

    def write_to_dir(
        self,
        output_dir: Path,
        output_file_name: str = "visualization.html",
        pbar: Optional[tqdm] = None,
    ):
        if output_dir.exists() and not output_dir.is_dir():
            raise ValueError("argument `output_dir` must be directory.")

        docs_dir = output_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        for element in self.elements.values():
            all_justifications = (
                element.informative_justifications + element.justified_by
            )
            renderable_justifications = [
                j for j in all_justifications if j.span_start and j.span_end
            ]
            for j in renderable_justifications:
                document_id = (
                    j.parent_id if j.parent_id else self.parent_child_map[j.child_id]
                )
                document = self.corpus[document_id]

                justification_document_html = render_single_justification_document(
                    document, j
                )

                rendered_html = Template(TEMPLATE).render(
                    document=immutabledict(
                        {
                            "id": document["parent_id"],
                            "title": get_title_sentence(document["fulltext"]),
                            "html": justification_document_html,
                            "span": f"{j.span_start}:{j.span_end}",
                        }
                    )
                )
                justification_file = (
                    docs_dir
                    / f"{document['parent_id']}_{j.span_start}-{j.span_end}.html"
                )
                justification_file.write_text(rendered_html)

                if pbar:
                    pbar.update()

        html_file = output_dir / output_file_name

        html_lines = [
            "<html>",
            '<head><link rel="stylesheet" href="style.css"></head>',
            "<body>",
        ]
        element_list_by_type = defaultdict(list)
        for element in self.elements.values():
            if element.element_type and "#" in element.element_type:
                _, element_type = split_uri(element.element_type)
            else:
                element_type = element.element_type
            element_list_by_type[element_type].append(element)

        for element_type, element_list in element_list_by_type.items():
            html_lines.append(f"<h1>{element_type}</h1>")
            for element in sorted(element_list, key=lambda e: e.element_id):
                rendered_element_html = self.render_element(element)
                html_lines.append(rendered_element_html)

        html_lines.extend(["</html>", "</body>"])
        rendered_html = "\n".join(html_lines)
        html_file.write_text(rendered_html)

        style_file = output_dir / "style.css"
        style_file.write_text(STYLE)

    def render_element(self, element: Element) -> str:
        html_lines = ["<div>"]
        if element.element_type and "#" in element.element_type:
            _, element_type = split_uri(element.element_type)
        else:
            element_type = element.element_type

        if "#" in element.element_id:
            _, element_id = split_uri(element.element_id)
        else:
            element_id = element.element_id

        justifications = element.informative_justifications + element.justified_by

        element_anchor = f'<u><span id="{element.element_id}">{element_id} ({element_type})</span></u>'

        html_lines.append(
            f"{element_anchor}: {self.render_justifications(justifications)}"
        )

        statement_list = self.render_statements(element.statements)

        if element.statements:
            html_lines.append(statement_list)

        if (
            element.names
            or element.handles
            or element.prototypes
            or element.members
            or element.clusters
        ):
            html_lines.append("<ul>")
            if element.names:
                html_lines.append(f"<li>names: {', '.join(element.names)}</li>")
            if element.handles:
                html_lines.append(f"<li>handles: {', '.join(element.handles)}</li>")
            if element.prototypes:
                html_lines.append(
                    f"<li>prototypes: {', '.join([self.anchor_link(p) for p in element.prototypes])}</li>"
                )
            if element.members:
                html_lines.append(
                    f"<li>members: {', '.join([self.anchor_link(p) for p in element.members])}</li>"
                )
            if element.clusters:
                html_lines.append(
                    f"<li>clusters: {', '.join([self.anchor_link(p) for p in element.clusters])}</li>"
                )
            html_lines.append("</ul>")
        html_lines.append("</div><br>")
        return "\n".join(html_lines)

    def render_statements(self, statements: List[Statement]) -> str:
        html_lines = ["<div>", "<ul>"]

        type_statements = [s for s in statements if s.predicate == RDF.type]
        nontype_statements = [s for s in statements if s.predicate != RDF.type]
        type_prefix = None

        if type_statements:
            type_statement = type_statements[0]
            _, type_prefix = split_uri(type_statement.object)
            html_lines.append(f"<li>{self._render_statement(type_statement)}</li>")

        for statement in nontype_statements:
            html_lines.append(
                f"<li>{self._render_statement(statement, type_prefix=type_prefix)}</li>"
            )

        html_lines.append("</ul>")
        html_lines.append("</div>")

        return "\n".join(html_lines)

    def _render_statement(
        self, statement: Statement, type_prefix: Optional[str] = None
    ) -> str:
        _, pred = split_uri(statement.predicate)

        if type_prefix:
            pred = pred.replace(type_prefix, "")

        return f"{pred}: {self.anchor_link(statement.object)} (Justified by {self.render_justifications(statement.justified_by)})"

    def render_justifications(self, justifications: List[Justification]) -> str:
        """Returns HTML for a comma-separated list of justification links"""

        rendered_justifications = set()
        for j in justifications:
            document_id = (
                j.parent_id if j.parent_id else self.parent_child_map[j.child_id]
            )
            if j.span_start and j.span_end:
                spanning_tokens = self.corpus[document_id]["fulltext"][
                    j.span_start : j.span_end + 1
                ]
                link = f'<a href=docs/{document_id}_{j.span_start}-{j.span_end}.html>"{spanning_tokens}" [{j.span_start}:{j.span_end}]</a>'
                rendered_justifications.update([link])
        return ", ".join(rendered_justifications)

    def anchor_link(self, element_id: URIRef) -> str:
        _, suffix = split_uri(element_id)
        return (
            f"<a href=#{element_id}>{suffix}</a>"
            if element_id in self.elements
            else suffix
        )
