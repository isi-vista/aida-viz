from rdflib import Graph, Namespace
from aida_interchange.rdf_ontologies import interchange_ontology

def aida_namespace(graph: Graph):
    try:
        aida = Namespace(dict(graph.namespace_manager.namespaces())["aida"])
    except KeyError:
        aida = interchange_ontology

    return aida
