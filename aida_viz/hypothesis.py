from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from aida_interchange.aida_rdf_ontologies import AIDA_ANNOTATION
from attr import attrib, attrs
from immutablecollections import (
    ImmutableDict,
    ImmutableSet,
    immutabledict,
    immutableset,
)
from rdflib import RDF, Graph
from rdflib.term import URIRef
from vistautils.misc_utils import flatten_once_to_list
from vistautils.span import Span

from aida_viz.corpus.core import Corpus

from .documents import (
    contexts_from_justifications,
    get_document,
    render_document,
    render_template,
)


class Cluster(NamedTuple):
    cluster_id: URIRef
    cluster_type: URIRef
    cluster_member_id: URIRef
    cluster_member_informative_justification: Tuple[
        Optional[str], Optional[str], int, int
    ]
    predicate_type: URIRef
    object_node: URIRef  # What is this?
    object_types: ImmutableSet[str]
    object_names: ImmutableSet[str]
    object_handles: ImmutableSet[str]
    informative_justification: Tuple[Optional[str], Optional[str], int, int]


class Statement(NamedTuple):
    predicate: URIRef
    object: URIRef
    object_names: List[str]
    object_handles: List[str]
    object_types: List[str]
    informative_justification: URIRef


class Justification(NamedTuple):
    parent_id: Optional[str]
    child_id: Optional[str]
    span_start: int
    span_end: int


@attrs(frozen=True, slots=True)
class Hypothesis:
    _name: str = attrib(converter=str)
    _events: ImmutableSet[Cluster] = attrib()
    _relations: ImmutableSet[Cluster] = attrib()
    _entities: ImmutableSet[Cluster] = attrib()

    @property
    def event_by_cluster(self) -> ImmutableDict[URIRef, List[Cluster]]:
        return self._by_cluster(self._events)

    @property
    def relation_by_cluster(self) -> ImmutableDict[URIRef, List[Cluster]]:
        return self._by_cluster(self._relations)

    @property
    def event_cluster_types(self) -> ImmutableDict[URIRef, URIRef]:
        return immutabledict(
            [(event.cluster_member_id, event.cluster_type) for event in self._events]
        )

    @property
    def relation_cluster_types(self) -> ImmutableDict[URIRef, URIRef]:
        return immutabledict(
            [
                (relation.cluster_member_id, relation.cluster_type)
                for relation in self._relations
            ]
        )

    @staticmethod
    def _by_cluster(
        items: ImmutableSet[Cluster]
    ) -> ImmutableDict[URIRef, List[Cluster]]:
        _item_by_cluster: Dict[URIRef, List[Cluster]] = {}

        for event in items:
            cluster = event.cluster_member_id

            if cluster not in _item_by_cluster:
                _item_by_cluster[cluster] = []

            _item_by_cluster[cluster].append(event)

        return immutabledict(_item_by_cluster)

    @staticmethod
    def from_graph(graph: Graph) -> "Hypothesis":
        all_clusters = sorted(graph.subjects(RDF.type, AIDA_ANNOTATION.SameAsCluster))
        event_clusters = immutableset(
            [
                cluster
                for cluster in all_clusters
                if all(
                    (event, RDF.type, AIDA_ANNOTATION.Event) in graph
                    for event in _entities_in_cluster(graph, cluster)
                )
            ]
        )
        events = _parse_clusters(event_clusters, graph)

        relation_clusters = immutableset(
            sorted(
                [
                    cluster
                    for cluster in all_clusters
                    if all(
                        (relation, RDF.type, AIDA_ANNOTATION.Relation) in graph
                        for relation in _entities_in_cluster(graph, cluster)
                    )
                ]
            )
        )
        relations = _parse_clusters(relation_clusters, graph)

        return Hypothesis(
            name=graph.value(predicate=RDF.type, object=AIDA_ANNOTATION.Hypothesis),
            events=events,
            relations=relations,
            entities=immutableset(),
        )

    @staticmethod
    def from_graph_by_elements(graph: Graph) -> "Hypothesis":
        event_elements: ImmutableSet[URIRef] = immutableset(
            graph.subjects(object=AIDA_ANNOTATION.Event)
        )
        events: ImmutableSet[Cluster] = _parse_elements(event_elements, graph)

        relation_elements: ImmutableSet[URIRef] = immutableset(
            graph.subjects(object=AIDA_ANNOTATION.Relation)
        )
        relations: ImmutableSet[Cluster] = _parse_elements(relation_elements, graph)

        return Hypothesis(
            name=graph.value(predicate=RDF.type, object=AIDA_ANNOTATION.Hypothesis),
            events=events,
            relations=relations,
            entities=immutableset(),
        )

    @staticmethod
    def from_graph_m36(graph: Graph) -> "Hypothesis":
        pass

    def visualize(
        self, output_dir: Path, output_file: Path, db_path: Path, verbose: bool
    ):
        _write_css_styling(output_dir / "style.css")

        output_lines = list()

        output_lines.append("<html>")
        output_lines.append("<head></head>")
        output_lines.append("<body>")
        output_lines.append(f"<b>Hypothesis Name: </b>{self._name}<br>")
        output_lines.append(
            "Note: Cluster handle is used when entity name is not found.<br>"
        )

        for cluster_id, events in self.event_by_cluster.items():
            event_cluster_type = self.event_cluster_types[cluster_id]
            event_cluster_type_rendered = event_cluster_type.split("#")[-1]
            output_lines.append(f"<br><u>Event: {event_cluster_type_rendered}</u><ul>")
            output_lines.extend(_render_cluster(events, output_dir, db_path, verbose))

        for cluster_id, relations in self.relation_by_cluster.items():
            relation_cluster_type = self.relation_cluster_types[cluster_id]
            relation_cluster_type_rendered = relation_cluster_type.split("#")[-1]
            output_lines.append(
                f"<br><u>Relation: {relation_cluster_type_rendered}</u><ul>"
            )
            output_lines.extend(
                _render_cluster(relations, output_dir, db_path, verbose)
            )

        output_lines.append("</body>")
        output_lines.append("</html>")

        with output_file.open("w", encoding="utf-8") as output:
            output.write("\n".join(output_lines))


def _render_cluster(
    clusters: Iterable[Cluster], output_dir: Path, db_path: Path, verbose: bool
) -> List[str]:

    output_lines = []
    current_cluster_member_id = None
    for cluster in sorted(
        clusters,
        key=lambda i: (i.cluster_member_id, i.cluster_member_informative_justification),
    ):

        # form sub-lists at the beginning of each new cluster
        if cluster.cluster_member_id != current_cluster_member_id:
            if current_cluster_member_id is not None:
                output_lines.append("</ul>")
            current_cluster_member_id = cluster.cluster_member_id

            _, cluster_member_informative_justification_link = _get_informative_justification_link(
                db_path,
                output_dir,
                Justification(
                    parent_id=cluster.cluster_member_informative_justification[0],
                    child_id=cluster.cluster_member_informative_justification[1],
                    span_start=cluster.cluster_member_informative_justification[2],
                    span_end=cluster.cluster_member_informative_justification[3],
                ),
            )
            output_lines.append("<li>")
            output_lines.append(
                f"ID: <a href={cluster_member_informative_justification_link}>{current_cluster_member_id.split('/')[-1]}</a>"
            )
            output_lines.append("<ul>")

        predicate_type_rendered = cluster.predicate_type.split("_")[-1]
        output_lines.append(f"<li><u>{predicate_type_rendered}:</u>")
        mention, informative_justification_link = _get_informative_justification_link(
            db_path,
            output_dir,
            Justification(
                parent_id=cluster.informative_justification[0],
                child_id=cluster.informative_justification[1],
                span_start=cluster.informative_justification[2],
                span_end=cluster.informative_justification[3],
            ),
        )
        if verbose:
            # Currently this program is written to expect the informative justification to exist.
            # If functionality is changed to no longer expect that, this would need to be changed
            # to accomadate for that.
            output_lines.append("<ul>")
            output_lines.append(
                f"<li><b>informativeJustification</b>: <a href={informative_justification_link}>{mention}</a></li>"
            )
            output_lines.append(
                f'<li><b>hasName</b>: {", ".join(cluster.object_names) or "Nothing found"}</li>'
            )
            output_lines.append(
                f'<li><b>handle</b>: {", ".join(cluster.object_handles) or "Nothing found"}</li>'
            )
            output_lines.append(
                f'<li><b>"type"</b>: {", ".join(cluster.object_types) or "Nothing found"}</li>'
            )
            output_lines.append("</ul>")
        else:
            object_line = f"<a href={informative_justification_link}>{mention}</a>"
            identifer_list = [
                *cluster.object_names,
                *cluster.object_handles,
                *cluster.object_types,
            ]
            if mention.split()[0] in identifer_list:
                identifer_list.remove(mention.split()[0])
            identifiers = immutableset(identifer_list)
            for identifier in identifiers:
                object_line += f", {identifier}"
            output_lines.append(object_line)
        output_lines.append("</li>")
    output_lines.append("</ul>")
    output_lines.append("</ul>")
    return output_lines


def _parse_clusters(
    clusters: ImmutableSet[URIRef], graph: Graph
) -> ImmutableSet[Cluster]:
    parsed_clusters = []

    for cluster in clusters:

        cluster_prototype = graph.value(
            subject=cluster, predicate=AIDA_ANNOTATION.prototype, any=False
        )

        cluster_prototype_types = _get_cluster_types(cluster_prototype, graph)

        if len(cluster_prototype_types) > 1:
            raise ValueError(
                "More than one cluster prototype; this should not be possible."
            )
        if not cluster_prototype_types:
            raise ValueError("No cluster prototype types found")
        cluster_type = cluster_prototype_types[0]

        cluster_members = sorted([m for m in _entities_in_cluster(graph, cluster)])

        for cluster_member in cluster_members:  #
            cluster_member_informative_justification = _get_informative_justification(
                cluster_member, graph
            )

            for statement in _parse_statements(graph, cluster_member):

                if statement.predicate != RDF.type:
                    parsed_clusters.append(
                        Cluster(
                            cluster,
                            cluster_type,
                            cluster_member,
                            cluster_member_informative_justification,
                            statement.predicate,
                            statement.object,
                            immutableset(statement.object_types),
                            immutableset(statement.object_names),
                            immutableset(statement.object_handles),
                            statement.informative_justification,
                        )
                    )

    return immutableset(parsed_clusters)


def _parse_elements(
    elements: ImmutableSet[URIRef], graph: Graph
) -> ImmutableSet[Cluster]:
    parsed_elements = []

    cluster_by_member = _get_cluster_by_member(graph)

    for element in elements:
        element_informative_justification = _get_informative_justification(
            element, graph
        )

        cluster = cluster_by_member.get(element, "No cluster found.")

        statements = _parse_statements(graph, element)
        type_statements = [s for s in statements if s.predicate == RDF.type]
        if len(type_statements) > 1:
            raise ValueError(
                "More than one cluster prototype; this should not be possible."
            )

        if not type_statements:
            element_type = None
        else:
            element_type = type_statements[0].object

        for statement in statements:

            if statement.predicate != RDF.type:
                parsed_elements.append(
                    Cluster(
                        cluster,
                        element_type,
                        element,
                        element_informative_justification,
                        statement.predicate,
                        statement.object,
                        immutableset(statement.object_types),
                        immutableset(statement.object_names),
                        immutableset(statement.object_handles),
                        statement.informative_justification,
                    )
                )

    return immutableset(sorted(parsed_elements, key=lambda e: e.cluster_member_id))


def _parse_statements(graph: Graph, element: URIRef):
    return [
        _parse_statement(graph, statement)
        for statement in sorted(graph.subjects(predicate=RDF.subject, object=element))
    ]


def _parse_statement(graph: Graph, statement: URIRef):
    """
    Parses a statement or assertion
    """

    statement_predicate = graph.value(
        subject=statement, predicate=RDF.predicate, any=False
    )
    statement_object = graph.value(subject=statement, predicate=RDF.object, any=False)
    statement_object_cluster_membership = graph.value(
        predicate=AIDA_ANNOTATION.clusterMember, object=statement_object
    )
    statement_object_cluster = graph.value(
        subject=statement_object_cluster_membership, predicate=AIDA_ANNOTATION.cluster
    )

    statement_object_names = [
        str(obj)
        for obj in graph.objects(
            subject=statement_object, predicate=AIDA_ANNOTATION.hasName
        )
    ]
    statement_object_names.sort()
    statement_object_handles = [
        str(obj)
        for obj in graph.objects(
            subject=statement_object_cluster, predicate=AIDA_ANNOTATION.handle
        )
    ]
    statement_object_handles.sort()

    rendered_object_types = [
        str(graph.value(subject=subj, predicate=RDF.object, any=False)).split("#")[-1]
        for subj in graph.subjects(predicate=RDF.subject, object=statement_object)
    ]
    rendered_object_types.sort()

    statement_object_informative_justification = _get_informative_justification(
        statement_object, graph
    )

    return Statement(
        predicate=statement_predicate,
        object=statement_object,
        object_names=statement_object_names,
        object_handles=statement_object_handles,
        object_types=rendered_object_types,
        informative_justification=statement_object_informative_justification,
    )


def _get_informative_justification(node: URIRef, graph: Graph) -> Justification:
    """
    Grabs the informative justification for a given RDF node and returns relavent information

    Returns None if no informative justification field is found (This behavior could change at a
    later date).
    """
    informative_justification = graph.value(
        subject=node, predicate=AIDA_ANNOTATION.informativeJustification, any=False
    )
    if informative_justification is not None:
        span_start = int(
            graph.value(
                subject=informative_justification,
                predicate=AIDA_ANNOTATION.startOffset,
                any=False,
            )
        )

        span_end = int(
            graph.value(
                subject=informative_justification,
                predicate=AIDA_ANNOTATION.endOffsetInclusive,
                any=False,
            )
        )

        source = graph.value(
            subject=informative_justification,
            predicate=AIDA_ANNOTATION.source,
            any=False,
        )

        source_doc = graph.value(
            subject=informative_justification,
            predicate=AIDA_ANNOTATION.sourceDocument,
            any=False,
        )

        return Justification(
            child_id=str(source) if source else None,
            parent_id=str(source_doc) if source_doc else None,
            span_start=span_start,
            span_end=span_end,
        )

    return Justification(None, None, 0, 0)


def _get_informative_justification_link(
    db_path: Path, output_dir: Path, informative_justification: Justification
) -> Tuple[str, Path]:
    doc_dir = output_dir / "docs"
    doc_dir.mkdir(exist_ok=True)

    child_id = informative_justification.child_id
    parent_id = informative_justification.parent_id
    span_start = informative_justification.span_start
    span_end = informative_justification.span_end

    if parent_id:
        parent_or_child_id = parent_id
    elif child_id:
        parent_or_child_id = child_id
    else:
        raise ValueError(
            "Informative justification must have either a parent id or a child id"
        )

    corpus = Corpus(db_path)
    output_file, mention = _render_html(
        corpus, doc_dir, parent_or_child_id, span_start, span_end
    )

    mention += f" ({span_start}:{span_end})"
    return mention, output_file.relative_to(output_dir)


def _render_html(
    corpus: Corpus, output_dir: Path, parent_or_child_id: str, start: int, end: int
) -> Tuple[Path, str]:
    """Outputs either the whole document rendered in HTML or a subspan. `end` is inclusive."""

    document = get_document(corpus, parent_or_child_id)
    if not document:
        raise ValueError(
            f"{document['parent_id']} not present in the document database."
        )

    justification_spans: ImmutableDict[str, Span] = immutabledict(
        {f"{start}:{end}": Span(start, end + 1)}
    )

    contexts = contexts_from_justifications(justification_spans, document)

    to_render, _ = render_document(document["fulltext"], justification_spans, contexts)
    if not to_render:
        raise ValueError("Could not find anything to render.")

    final_html = render_template(
        document=immutabledict(
            {
                "id": document["parent_id"],
                "title": document["title"],
                "html": to_render,
                "span": f"{start}:{end}",
            }
        )
    )
    output_file = output_dir / f"{document['parent_id']}_{start}-{end}.html"
    output_file.write_text(final_html)

    return output_file, document["fulltext"][start : end + 1]


def _entities_in_cluster(g: Graph, cluster: URIRef) -> ImmutableSet[URIRef]:
    return immutableset(
        flatten_once_to_list(
            g.objects(cluster_membership, AIDA_ANNOTATION.clusterMember)
            for cluster_membership in g.subjects(AIDA_ANNOTATION.cluster, cluster)
        )
    )


def _get_cluster_types(cluster: URIRef, graph: Graph):
    return [
        graph.value(subject=prototype_subj, predicate=RDF.object, any=False)
        for prototype_subj in graph.subjects(predicate=RDF.subject, object=cluster)
        if (prototype_subj, RDF.predicate, RDF.type) in graph
    ]


def _get_cluster_by_member(graph: Graph):
    cluster_by_member = {}

    for membership in graph.subjects(object=AIDA_ANNOTATION.ClusterMembership):
        cluster = graph.value(subject=membership, predicate=AIDA_ANNOTATION.cluster)
        member = graph.value(
            subject=membership, predicate=AIDA_ANNOTATION.clusterMember
        )

        if member not in cluster_by_member:
            cluster_by_member[member] = cluster
        else:
            raise ValueError(
                f"Member {member} assigned to more than one cluster. This should not happen."
            )

    return cluster_by_member


def _write_css_styling(css_file: Path):
    css_file.write_text(
        """
body {
  padding: 2.5%
}

.text-center{
  text-align:center
}

.text-left{
  text-align:left
}

.document-details-modal.modal-body {
  max-height: 80vh;
  overflow-y: auto;
  white-space: pre-wrap;
}

.card {
  position: relative;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-orient: vertical;
  -webkit-box-direction: normal;
  -ms-flex-direction: column;
  flex-direction: column;
  min-width: 0;
  word-wrap: break-word;
  background-color: #fff;
  background-clip: border-box;
  border: 1px solid rgba(0, 0, 0, .125);
  border-radius: .25rem;
  width: 100%;
  height: 100%;
  margin: 0 auto;
  float: none;
  margin-bottom: 20px;
}

.card-header {
  padding: .75rem 1.25rem;
  margin-bottom: 0;
  background-color: rgba(0, 0, 0, .03);
  border-bottom: 1px solid rgba(0, 0, 0, .125)
}

.card-body {
  -webkit-box-flex: 1;
  -ms-flex: 1 1 auto;
  flex: 1 1 auto;
  padding: 1.25rem
}

.mention-card-body-context:hover {
  text-decoration: underline;
}

.card-group {
  width: 100%;
  margin: 0 auto; /* Added */
  float: none; /* Added */
  margin-bottom: 10px; /* Added */
}

.bg-light-custom {
  background: #e6e6e6;
}

span.mention.primary-mention {
  background-color: #ffc107
}

span.mention {
  background-color: #FFFF00
}

span.mention-context {
  font-weight: bold
}

ul{
  padding-left: 20px;
}

.table-hover tbody tr:hover td, .table-hover tbody tr:hover th {
  background-color: rgb(66,139,202,0.5) ;
}
"""
    )
