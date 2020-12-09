import argparse
from pathlib import Path

from rdflib import RDF, Graph, Namespace
from tqdm import tqdm

from aida_viz.corpus.core import Corpus
from aida_viz.elements import Element
from aida_viz.htmlwriter.core import HtmlWriter
from aida_viz.hypothesis import Hypothesis

USAGE = """Visualize AIDA AIF graphs (in RDF "turtle" format, extension .ttl) as explorable HTML pages."""


def getargs():
    parser = argparse.ArgumentParser(description=USAGE)
    arg = parser.add_argument

    arg("-a", "--aif_file", type=Path, help="AIF file to be visualized", required=True)
    arg(
        "-d",
        "--db",
        type=Path,
        help="sqlite database containing the necessary documents for visualization.",
        dest="db_path",
        required=True,
    )
    arg(
        "-o",
        "--out",
        type=Path,
        help="Directory to output the visualization. Overwrites any files matching the naming scheme.",
        dest="out_dir",
        default="./aida-viz-html",
    )
    arg("--by_clusters", action="store_true")
    arg("--verbose", "-v", action="store_true")

    return parser.parse_args()


def main(
    aif_file: Path, out_dir: Path, db_path: Path, by_clusters: bool, verbose: bool
) -> Path:
    graph: Graph = Graph()
    graph.parse(source=str(aif_file), format="turtle")
    aida = Namespace(dict(graph.namespace_manager.namespaces())["aida"])

    if by_clusters:
        out_dir.mkdir(exist_ok=True)
        if verbose:
            output_file = out_dir / f"{aif_file.stem}_visualization_verbose.html"
        else:
            output_file = out_dir / f"{aif_file.stem}_visualization.html"
        output_file.touch(exist_ok=True)
        hypothesis = Hypothesis.from_graph(graph)
        hypothesis.visualize(out_dir, output_file, db_path, verbose)
    else:
        entities = list(graph.subjects(predicate=RDF.type, object=aida.Entity))
        events = list(graph.subjects(predicate=RDF.type, object=aida.Event))
        relations = list(graph.subjects(predicate=RDF.type, object=aida.Relation))
        clusters = list(graph.subjects(predicate=RDF.type, object=aida.SameAsCluster))

        element_ids = clusters + entities + events + relations
        elements = {
            element_id: Element.from_uriref(element_id, graph=graph)
            for element_id in tqdm(element_ids)
        }

        corpus = Corpus(db_path)
        renderer = HtmlWriter(corpus, elements, directory=out_dir)
        renderer.write_to_dir(output_file_name=f"{aif_file.stem}.html")
    return out_dir


# pylint: disable=C0103
if __name__ == "__main__":
    args = getargs()
    output = main(**vars(args))

    print(f"Vizualization: {output}")
