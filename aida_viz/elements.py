import json
from typing import List, NamedTuple, Optional, Tuple

from rdflib import RDF, Graph, Namespace, URIRef

from aida_viz.utils import aida_namespace

class Element(NamedTuple):
    element_id: URIRef
    element_type: URIRef
    prototypes: List[URIRef] = []
    members: List[URIRef] = []
    clusters: List[URIRef] = []
    names: List[str] = []
    handles: List[str] = []
    informative_justifications: List["Justification"] = []
    justified_by: List["Justification"] = []
    statements: List["Statement"] = []
    link_assertions: List["LinkAssertion"] = []
    private_data: List[Tuple[str, str]] = []

    @staticmethod
    def from_uriref(element_id: URIRef, *, graph: Graph):

        aida = aida_namespace(graph=graph)

        informativejustification_ids = [
            j
            for j in graph.objects(
                subject=element_id, predicate=aida.informativeJustification
            )
            if (j, RDF.type, aida.TextJustification) in graph
        ]

        justifiedby_ids = [
            j
            for j in graph.objects(subject=element_id, predicate=aida.justifiedBy)
            if (j, RDF.type, aida.TextJustification) in graph
        ]
        statement_ids = list(graph.subjects(predicate=RDF.subject, object=element_id))

        link_assertion_ids = list(
            graph.objects(subject=element_id, predicate=aida.link)
        )

        return Element(
            element_id=element_id,
            element_type=graph.value(subject=element_id, predicate=RDF.type, any=False),
            prototypes=list(
                graph.objects(subject=element_id, predicate=aida.prototype)
            ),
            members=list(
                graph.objects(subject=element_id, predicate=aida.clusterMember)
            ),
            clusters=list(graph.objects(subject=element_id, predicate=aida.cluster)),
            names=list(graph.objects(subject=element_id, predicate=aida.hasName)),
            handles=list(graph.objects(subject=element_id, predicate=aida.handle)),
            informative_justifications=[
                Justification.from_uriref(inf_j, graph=graph)
                for inf_j in informativejustification_ids
            ],
            justified_by=[
                Justification.from_uriref(j, graph=graph) for j in justifiedby_ids
            ],
            statements=[Statement.from_uriref(s, graph=graph) for s in statement_ids],
            link_assertions=[
                LinkAssertion.from_uriref(l, graph=graph) for l in link_assertion_ids
            ],
            private_data=private_data(element_id, graph=graph),
        )


class Statement(NamedTuple):
    statement_id: URIRef
    subject: URIRef
    predicate: URIRef
    object: URIRef
    justified_by: List["Justification"] = []

    @staticmethod
    def from_uriref(statement_id: URIRef, *, graph: Graph):
        aida = aida_namespace(graph=graph)

        statement_subject = graph.value(
            subject=statement_id, predicate=RDF.subject, any=False
        )
        statement_predicate = graph.value(
            subject=statement_id, predicate=RDF.predicate, any=False
        )
        statement_object = graph.value(
            subject=statement_id, predicate=RDF.object, any=False
        )
        justifiedby_ids = list(
            graph.objects(subject=statement_id, predicate=aida.justifiedBy)
        )

        textjustification_ids = [
            node
            for node in justifiedby_ids
            if (node, RDF.type, aida.TextJustification) in graph
        ]
        compoundjustification_ids = [
            node
            for node in justifiedby_ids
            if (node, RDF.type, aida.CompoundJustification) in graph
        ]

        for cj in compoundjustification_ids:
            textjustification_ids.extend(
                graph.objects(subject=cj, predicate=aida.containedJustification)
            )

        return Statement(
            statement_id=statement_id,
            subject=statement_subject,
            predicate=statement_predicate,
            object=statement_object,
            justified_by=[
                Justification.from_uriref(j, graph=graph) for j in textjustification_ids
            ],
        )


class Justification(NamedTuple):
    justification_id: URIRef
    parent_id: Optional[str]
    child_id: Optional[str]
    span_start: Optional[int]
    span_end: Optional[int]
    private_data: List[Tuple[str, str]] = []

    @staticmethod
    def from_uriref(justification_id: URIRef, *, graph: Graph):
        aida = aida_namespace(graph=graph)

        if not (justification_id, RDF.type, aida.TextJustification) in graph:
            raise ValueError(
                f"{justification_id} does not have type TextJustification in graph."
            )

        span_start = graph.value(
            subject=justification_id, predicate=aida.startOffset, any=False
        )

        span_end = graph.value(
            subject=justification_id, predicate=aida.endOffsetInclusive, any=False
        )

        source = graph.value(subject=justification_id, predicate=aida.source, any=False)

        source_doc = graph.value(
            subject=justification_id, predicate=aida.sourceDocument, any=False
        )

        return Justification(
            justification_id=justification_id,
            child_id=str(source) if source else None,
            parent_id=str(source_doc) if source_doc else None,
            span_start=int(span_start) if span_start else None,
            span_end=int(span_end) if span_end else None,
            private_data=private_data(justification_id, graph=graph),
        )


class LinkAssertion(NamedTuple):
    link_id: URIRef
    link_confidence: float
    link_target: str
    link_system: URIRef

    @staticmethod
    def from_uriref(link_id: URIRef, *, graph):
        aida = aida_namespace(graph=graph)

        target = graph.value(subject=link_id, predicate=aida.linkTarget)
        system = graph.value(subject=link_id, predicate=aida.system)
        confidence = graph.value(
            subject=graph.value(subject=link_id, predicate=aida.confidence),
            predicate=aida.confidenceValue,
        )

        return LinkAssertion(
            link_id=link_id,
            link_confidence=float(confidence),
            link_target=target,
            link_system=system,
        )


def private_data(subject_id: URIRef, *, graph: Graph):
    aida = aida_namespace(graph=graph)
    json_pairs = []
    for private_data_node in graph.objects(
        subject=subject_id, predicate=aida.privateData
    ):
        for literal in graph.objects(
            subject=private_data_node, predicate=aida.jsonContent
        ):
            for pair in json.loads(str(literal)).items():
                json_pairs.append(pair)

    return json_pairs
