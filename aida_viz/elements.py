from typing import List, NamedTuple, Optional

from aida_interchange.rdf_ontologies import interchange_ontology as AIDA_ANNOTATION
from rdflib import RDF, Graph, URIRef


class Element(NamedTuple):
    element_id: URIRef
    element_type: URIRef
    prototype: Optional[URIRef] = None
    names: Optional[List[str]] = []
    handles: Optional[List[str]] = []
    informative_justifications: List["Justification"] = []
    justified_by: List["Justification"] = []
    statements: List["Statement"] = []

    @staticmethod
    def from_uriref(element_id: URIRef, *, graph: Graph):
        informativejustification_ids = list(
            graph.objects(
                subject=element_id, predicate=AIDA_ANNOTATION.informativeJustification
            )
        )
        justifiedby_ids = list(
            graph.objects(subject=element_id, predicate=AIDA_ANNOTATION.justifiedBy)
        )
        statement_ids = list(graph.subjects(predicate=RDF.subject, object=element_id))

        return Element(
            element_id=element_id,
            element_type=graph.value(subject=element_id, predicate=RDF.type, any=False),
            prototype=graph.value(
                subject=element_id, predicate=AIDA_ANNOTATION.prototype, any=False
            ),
            names=list(
                graph.objects(subject=element_id, predicate=AIDA_ANNOTATION.hasName)
            ),
            handles=list(
                graph.objects(subject=element_id, predicate=AIDA_ANNOTATION.handle)
            ),
            informative_justifications=[
                Justification.from_uriref(inf_j, graph=graph)
                for inf_j in informativejustification_ids
            ],
            justified_by=[
                Justification.from_uriref(j, graph=graph) for j in justifiedby_ids
            ],
            statements=[Statement.from_uriref(s, graph=graph) for s in statement_ids],
        )


class Statement(NamedTuple):
    statement_id: URIRef
    subject: URIRef
    predicate: URIRef
    object: URIRef
    justified_by: List["Justification"] = []

    @staticmethod
    def from_uriref(statement_id: URIRef, *, graph: Graph):
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
            graph.objects(subject=statement_id, predicate=AIDA_ANNOTATION.justifiedBy)
        )

        textjustification_ids = [
            node
            for node in justifiedby_ids
            if (node, RDF.type, AIDA_ANNOTATION.TextJustification) in graph
        ]
        compoundjustification_ids = [
            node
            for node in justifiedby_ids
            if (node, RDF.type, AIDA_ANNOTATION.CompoundJustification) in graph
        ]

        for cj in compoundjustification_ids:
            textjustification_ids.extend(
                graph.objects(
                    subject=cj, predicate=AIDA_ANNOTATION.containedJustification
                )
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
    span_start: int
    span_end: int

    @staticmethod
    def from_uriref(justification_id: URIRef, *, graph: Graph):
        if not (justification_id, RDF.type, AIDA_ANNOTATION.TextJustification) in graph:
            print(f"{justification_id} does not have type TextJustification in graph.")

        span_start = graph.value(
            subject=justification_id, predicate=AIDA_ANNOTATION.startOffset, any=False
        )

        span_end = graph.value(
            subject=justification_id,
            predicate=AIDA_ANNOTATION.endOffsetInclusive,
            any=False,
        )

        source = graph.value(
            subject=justification_id, predicate=AIDA_ANNOTATION.source, any=False
        )

        source_doc = graph.value(
            subject=justification_id,
            predicate=AIDA_ANNOTATION.sourceDocument,
            any=False,
        )

        if span_start and span_end and (source or source_doc):
            return Justification(
                justification_id=justification_id,
                child_id=str(source) if source else None,
                parent_id=str(source_doc) if source_doc else None,
                span_start=int(span_start),
                span_end=int(span_end),
            )
        else:
            print(
                ValueError(
                    f"{justification_id} requires span start and end, and one of source or source_doc"
                )
            )
