from typing import List, NamedTuple, Optional

from rdflib import RDF, Graph, Namespace, URIRef


class Element(NamedTuple):
    element_id: URIRef
    element_type: URIRef
    prototypes: List[URIRef] = []
    names: List[str] = []
    handles: List[str] = []
    informative_justifications: List["Justification"] = []
    justified_by: List["Justification"] = []
    statements: List["Statement"] = []

    @staticmethod
    def from_uriref(element_id: URIRef, *, graph: Graph):
        aida = Namespace(dict(graph.namespace_manager.namespaces())["aida"])

        informativejustification_ids = list(
            graph.objects(subject=element_id, predicate=aida.informativeJustification)
        )
        justifiedby_ids = list(
            graph.objects(subject=element_id, predicate=aida.justifiedBy)
        )
        statement_ids = list(graph.subjects(predicate=RDF.subject, object=element_id))

        return Element(
            element_id=element_id,
            element_type=graph.value(subject=element_id, predicate=RDF.type, any=False),
            prototypes=list(
                graph.objects(subject=element_id, predicate=aida.prototype)
            ),
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
        )


class Statement(NamedTuple):
    statement_id: URIRef
    subject: URIRef
    predicate: URIRef
    object: URIRef
    justified_by: List["Justification"] = []

    @staticmethod
    def from_uriref(statement_id: URIRef, *, graph: Graph):
        aida = Namespace(dict(graph.namespace_manager.namespaces())["aida"])

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
    span_start: int
    span_end: int

    @staticmethod
    def from_uriref(justification_id: URIRef, *, graph: Graph):
        aida = Namespace(dict(graph.namespace_manager.namespaces())["aida"])

        if not (justification_id, RDF.type, aida.TextJustification) in graph:
            print(f"{justification_id} does not have type TextJustification in graph.")

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
