import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict

from rdflib import RDF, Graph, URIRef
from tqdm import tqdm

from aida_viz.corpus.core import Corpus
from aida_viz.elements import Element
from aida_viz.htmlwriter.core import HtmlWriter
from aida_viz.utils import aida_namespace


def main(aif_file: Path, corpus_path: Path, out_dir: Path):
    corpus = Corpus(corpus_path)
    graph = Graph()
    
    print('parsing graph...')
    graph.parse(source=str(aif_file), format="turtle")
    print('done.')
    aida = aida_namespace(graph)
    cluster_ids = list(graph.subjects(predicate=RDF.type, object=aida.SameAsCluster))
    cluster_element_maps = {}
    for cluster_id in tqdm(cluster_ids, desc="parsing elements in clusters"):
        cluster_element = Element.from_uriref(cluster_id, graph=graph)
        membership_ids = list(
            graph.subjects(predicate=aida.cluster, object=URIRef(cluster_id))
        )
        membership_elements = [
            Element.from_uriref(membership_id, graph=graph)
            for membership_id in membership_ids
        ]

        if len(membership_elements) > 1:

            entity_ids = [
                m for membership in membership_elements for m in membership.members
            ]
            entity_elements = [
                Element.from_uriref(entity_id, graph=graph) for entity_id in entity_ids
            ]

            element_by_id = {
                e.element_id: e
                for e in [cluster_element] + membership_elements + entity_elements
            }
            cluster_element_maps[cluster_id] = element_by_id

    for i, element_by_id in enumerate(cluster_element_maps.values()):
        writer = HtmlWriter(corpus=corpus, elements=element_by_id)
        writer.write_to_dir(out_dir, f"{i:04}.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize AIF file (.ttl extension)")
    parser.add_argument(
        "-a", "--aif_file", type=Path, help="AIF file to be visualized", required=True
    )
    parser.add_argument(
        "-c",
        "--corpus",
        type=Path,
        help="A Corpus sqlite file",
        dest="corpus_path",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        help="Directory to output the visualization. Overwrites any files matching the naming scheme.",
        dest="out_dir",
        default="./visualizer_results",
    )
    args = parser.parse_args()
    main(args.aif_file, args.corpus_path, args.out_dir)

    print(f"Saved visualization at {args.out_dir}")
