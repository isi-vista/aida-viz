import argparse
from pathlib import Path

from rdflib import Graph

from aida_viz.hypothesis import Hypothesis


def main(
    aif_file: Path, out_dir: Path, db_path: Path, verbose: bool, by_elements: bool
) -> Path:
    graph = Graph()
    graph.parse(source=str(aif_file), format="turtle")

    out_dir.mkdir(exist_ok=True)
    if verbose:
        output_file = out_dir / f"{aif_file.stem}_visualization_verbose.html"
    else:
        output_file = out_dir / f"{aif_file.stem}_visualization.html"
    output_file.touch(exist_ok=True)

    if by_elements:
        hypothesis = Hypothesis.from_graph_by_elements(graph)
    else:
        hypothesis = Hypothesis.from_graph(graph)

    hypothesis.visualize(out_dir, output_file, db_path, verbose)

    return output_file


# pylint: disable=C0103
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize ta3 output for AIDA")
    parser.add_argument(
        "-a", "--aif_file", type=Path, help="AIF file to be visualized", required=True
    )
    parser.add_argument(
        "-d",
        "--db",
        type=Path,
        help="sqlite database containing the necessary documents for visualization (default=$AIDA_HYPOTH_VIZ_DIR/databases/documents.sqlite)",
        dest="db_path",
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
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--by_elements", action="store_true")

    output = main(**vars(parser.parse_args()))

    print(f"Vizualization file: {output}")
