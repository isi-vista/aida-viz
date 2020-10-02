from rdflib import Graph, Namespace


def aida_namespace(graph: Graph):
    return Namespace(dict(graph.namespace_manager.namespaces())["aida"])
