from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

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

from aida_interchange.aida_rdf_ontologies import AIDA_ANNOTATION

from .documents import render_html

# Typing aliases
Justification = Tuple[str, str, int, int]
Cluster = Tuple[
    URIRef,
    URIRef,
    URIRef,
    Justification,
    URIRef,
    URIRef,
    ImmutableSet[str],
    ImmutableSet[str],
    ImmutableSet[str],
    Justification,
]

CONTACT = "Contact"
ENTITY_PREDICATE = "EntityOrFiller"
LOCATED_NEAR = "Physical.LocatedNear"
MOVEMENT_TRANSPORT = "Movement.Transport"
ORG_AFFILIATION = "OrganizationAffiliation"
PART_WHOLE = "PartWhole"
PLACE_PREDICATE = "Place"
PLACE_TYPES = {"FAC", "GPE", "LOC"}
SPONSORSHIP = "GeneralAffiliation.Sponsorship"


@attrs(frozen=True, slots=True)
class Hypothesis:
    _name: str = attrib(converter=str)
    _events: ImmutableSet[Cluster] = attrib()
    _relations: ImmutableSet[Cluster] = attrib()

    @property
    def event_by_cluster(self) -> ImmutableDict[URIRef, List[Cluster]]:
        return self._by_cluster(self._events)

    @property
    def relation_by_cluster(self) -> ImmutableDict[URIRef, List[Cluster]]:
        return self._by_cluster(self._relations)

    @property
    def event_cluster_types(self) -> ImmutableDict[URIRef, URIRef]:
        return immutabledict(
            [event[:2] for event in self._events]
        )  # id/type are the 1/2nd items in the tuple

    @property
    def relation_cluster_types(self) -> ImmutableDict[URIRef, URIRef]:
        return immutabledict(
            [relation[:2] for relation in self._relations]
        )  # id/type are the 1/2nd items in the tuple

    @staticmethod
    def _by_cluster(
        items: ImmutableSet[Cluster]
    ) -> ImmutableDict[URIRef, List[Cluster]]:
        _item_by_cluster: Dict[URIRef, List[Cluster]] = defaultdict(list)
        for event in items:
            cluster = event[0]  # the first member of the tuple is the cluster-level id
            _item_by_cluster[cluster].append(
                event
            )  # cluster-level id/type are at indices 0/1
        return immutabledict(_item_by_cluster)

    @staticmethod
    def from_graph(graph: Graph) -> "Hypothesis":
        all_clusters = sorted(graph.subjects(RDF.type, AIDA_ANNOTATION.SameAsCluster))

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
        events = _parse_clusters(event_clusters, graph, relations)

        return Hypothesis(
            name=graph.value(predicate=RDF.type, object=AIDA_ANNOTATION.Hypothesis),
            events=events,
            relations=relations,
        )

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
    items: Iterable[Cluster], output_dir: Path, db_path: Path, verbose: bool
) -> List[str]:
    output_lines = []

    current_cluster_member_id = None
    for relation in sorted(
        items, key=lambda i: (i[2], i[3])
    ):  # sort first by cluster, then by predicate
        _, _, cluster_member_id, cluster_member_informative_justification, predicate_type, _, object_types, object_names, object_handles, informative_justification = (
            relation
        )

        # form sub-lists at the beginning of each new cluster
        if cluster_member_id != current_cluster_member_id:
            if current_cluster_member_id is not None:
                output_lines.append("</ul>")
            current_cluster_member_id = cluster_member_id
            _, cluster_member_informative_justification_link = _get_informative_justification_link(
                db_path, output_dir, cluster_member_informative_justification
            )
            output_lines.append("<li>")
            output_lines.append(
                f"ID: <a href={cluster_member_informative_justification_link}>{current_cluster_member_id.split('/')[-1]}</a>"
            )
            output_lines.append("<ul>")

        predicate_type_rendered = predicate_type.split("_")[-1]
        output_lines.append(f"<li><u>{predicate_type_rendered}:</u>")
        mention, informative_justification_link = _get_informative_justification_link(
            db_path, output_dir, informative_justification
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
                f'<li><b>hasName</b>: {", ".join(object_names) or "Nothing found"}</li>'
            )
            output_lines.append(
                f'<li><b>handle</b>: {", ".join(object_handles) or "Nothing found"}</li>'
            )
            output_lines.append(
                f'<li><b>"type"</b>: {", ".join(object_types) or "Nothing found"}</li>'
            )
            output_lines.append("</ul>")
        else:
            object_line = f"<a href={informative_justification_link}>{mention}</a>"
            identifier_list = [*object_names, *object_handles, *object_types]
            if mention.split()[0] in identifier_list:
                identifier_list.remove(mention.split()[0])
            identifiers = immutableset(identifier_list)
            for identifier in identifiers:
                object_line += f", {identifier}"
            output_lines.append(object_line)
        output_lines.append("</li>")
    output_lines.append("</ul>")
    output_lines.append("</ul>")
    return output_lines


def _parse_clusters(
    clusters: ImmutableSet[URIRef],
    graph: Graph,
    relations: ImmutableSet[Cluster] = None,
) -> ImmutableSet[Cluster]:
    parsed_clusters = []
    events_by_cluster: Dict[URIRef, List[Cluster]] = defaultdict(list)

    for cluster in clusters:
        cluster_prototype = graph.value(
            subject=cluster, predicate=AIDA_ANNOTATION.prototype, any=False
        )
        cluster_prototype_types = [
            graph.value(subject=prototype_subj, predicate=RDF.object, any=False)
            for prototype_subj in graph.subjects(
                predicate=RDF.subject, object=cluster_prototype
            )
            if (prototype_subj, RDF.predicate, RDF.type) in graph
        ]

        if len(cluster_prototype_types) != 1:
            raise ValueError(
                "More than one cluster prototype; this should not be possible."
            )
        cluster_type = cluster_prototype_types[0]

        cluster_members = sorted([m for m in _entities_in_cluster(graph, cluster)])
        for cluster_member in cluster_members:
            for member_node in sorted(
                graph.subjects(predicate=RDF.subject, object=cluster_member)
            ):
                cluster_member_informative_justification = _get_informative_justification(
                    cluster_member, graph
                )

                predicate_type = graph.value(
                    subject=member_node, predicate=RDF.predicate, any=False
                )
                object_node = graph.value(
                    subject=member_node, predicate=RDF.object, any=False
                )
                cluster_membership_node = graph.value(
                    predicate=AIDA_ANNOTATION.clusterMember, object=object_node
                )
                cluster_node = graph.value(
                    subject=cluster_membership_node, predicate=AIDA_ANNOTATION.cluster
                )

                object_names = [
                    str(obj)
                    for obj in graph.objects(
                        subject=object_node, predicate=AIDA_ANNOTATION.hasName
                    )
                ]
                object_names.sort()
                object_handles = [
                    str(obj)
                    for obj in graph.objects(
                        subject=cluster_node, predicate=AIDA_ANNOTATION.handle
                    )
                ]
                object_handles.sort()
                rendered_object_types = [
                    str(
                        graph.value(subject=subj, predicate=RDF.object, any=False)
                    ).split("#")[-1]
                    for subj in graph.subjects(
                        predicate=RDF.subject, object=object_node
                    )
                ]
                rendered_object_types.sort()
                informative_justification = _get_informative_justification(
                    object_node, graph
                )

                if predicate_type != RDF.type:
                    if informative_justification == (
                        "",
                        "",
                        0,
                        0,
                    ) or cluster_member_informative_justification == ("", "", 0, 0):
                        print(
                            "One or both of the informative justifications for this cluster member "
                            "was not found. As such it might be displayed incorrectly and/or with "
                            "a broken link. Please contact one of the maintainers of this "
                            "repository for more details or to fix this issue."
                        )
                    parsed_member = (
                        cluster,
                        cluster_type,
                        cluster_member,
                        cluster_member_informative_justification,
                        predicate_type,
                        object_node,
                        immutableset(rendered_object_types),
                        immutableset(object_names),
                        immutableset(object_handles),
                        informative_justification,
                    )
                    parsed_clusters.append(parsed_member)
                    events_by_cluster[cluster].append(parsed_member)

    # Handle missing Place arguments for events
    if relations:

        # Group relation members by relation
        # while filtering out irrelevant ones
        relations_by_cluster: Dict[URIRef, List[Cluster]] = defaultdict(list)
        # I'm assuming that input hypothesis files normally link to
        # more than one document
        docs_to_locations: Dict[str, List[Justification]] = defaultdict(list)
        locations_to_data = {}
        location_map: Dict[Justification, Justification] = {}
        for relation in relations:
            relation_type = relation[1].split("#")[-1]
            predicate_type = relation[4].split("_")[-1]
            if relation_type == LOCATED_NEAR:
                relations_by_cluster[relation[0]].append(relation)
                # Create list of places for potential use later
                if predicate_type.split("_")[-1] == PLACE_PREDICATE:
                    docs_to_locations[relation[9][1]].append(relation[9])
                    locations_to_data[relation[9]] = (
                        relation[5],
                        relation[6],
                        relation[7],
                        relation[8],
                    )
            elif (
                relation_type.startswith(PART_WHOLE)
                or relation_type.startswith(ORG_AFFILIATION)
                or relation_type == SPONSORSHIP
            ):
                relations_by_cluster[relation[0]].append(relation)
        # Create map from locations to broader areas
        for relation_cluster in relations_by_cluster.values():
            relation_place = None
            relation_entity = None
            for relation in relation_cluster:
                predicate_type = relation[4].split("_")[-1]
                if predicate_type == ENTITY_PREDICATE:
                    for object_type in relation[6]:
                        if any(loc_type in object_type for loc_type in PLACE_TYPES):
                            relation_entity = relation[9]
                elif predicate_type == PLACE_PREDICATE:
                    relation_place = relation[9]
            if relation_place and relation_entity:
                location_map[relation_entity] = relation_place

        # For each event cluster, try to identify the Place based on
        # relations, existing arguments, or trends in the document
        # if there is no Place argument filler already.
        for cluster in events_by_cluster.values():
            cluster_predicates = {member[4].split("_")[-1] for member in cluster}
            cluster_type = cluster[0][1].split("#")[-1]
            if (
                PLACE_PREDICATE not in cluster_predicates
                and MOVEMENT_TRANSPORT not in cluster_type
            ):
                location_from_relation = _get_place_from_relation_or_argument(
                    cluster, cluster_type, relations_by_cluster
                )
                if location_from_relation:
                    parsed_clusters.append(location_from_relation)
                else:
                    # As a final resort, choose the most frequently used location in the document
                    # and find its broadest location to use as the default Place.
                    # This assumes that there is at least one location
                    # identified in the given document.
                    # For now, grab the document from the first informative justification.
                    cluster_doc = cluster[0][9][1]
                    doc_locations = Counter(docs_to_locations[cluster_doc])
                    most_common_location = doc_locations.most_common(1)[0][0]
                    default_location = _get_higher_level_location(
                        most_common_location, location_map
                    )
                    default_location_info = locations_to_data[default_location]

                    parsed_clusters.append(
                        (
                            cluster[0][0],
                            cluster[0][1],
                            cluster[0][2],
                            cluster[0][3],
                            cluster[0][1] + "_" + PLACE_PREDICATE,
                            default_location_info[0],
                            default_location_info[1],
                            default_location_info[2],
                            default_location_info[3],
                            default_location,
                        )
                    )

    return immutableset(parsed_clusters)


def _get_place_from_relation_or_argument(
    event_cluster: List[Cluster],
    cluster_type: str,
    relations_by_cluster: Dict[URIRef, List[Cluster]],
) -> Optional[Cluster]:
    """
    Attempts to find a location that is related to a
    cluster entity
    If there is no linked "place" relation, it will attempt to
    use an existing argument filler. For example, if the Target
    of a Conflict.Attack event is a GPE, it may be used as the
    Place for that event.
    TODO: prioritize certain arguments?
    for example, an Attacker of a Conflict.Attack event is less
    likely to be the location of the event
    Returns None if no matching location relation is found.
    """
    location_clusters = []
    part_whole_clusters = []
    affiliation_clusters = []
    for relation_cluster in relations_by_cluster.values():
        for relation_member in relation_cluster:
            relation_type_string = relation_member[1].split("#")[-1]
            if relation_type_string == LOCATED_NEAR:
                for member in event_cluster:
                    if relation_member[9] == member[9]:
                        if relation_member[3] == member[3]:
                            # If both justifications match, use that relation.
                            # Find the corresponding Place argument
                            # in this "matching" cluster.
                            for place_relation_member in relation_cluster:
                                relation_predicate = place_relation_member[4].split(
                                    "_"
                                )[-1]
                                if relation_predicate == PLACE_PREDICATE:
                                    return _create_place_cluster(
                                        member, place_relation_member
                                    )
                        else:
                            # Else, save it to possibly examine later
                            location_clusters.append(relation_cluster)
            elif relation_type_string.startswith(PART_WHOLE):
                for member in event_cluster:
                    if relation_member[9] == member[9]:
                        part_whole_clusters.append(relation_cluster)
            elif relation_type_string.startswith(ORG_AFFILIATION):
                for member in event_cluster:
                    if relation_member[9] == member[9]:
                        affiliation_clusters.append(relation_cluster)
            elif relation_type_string == SPONSORSHIP and cluster_type.startswith(
                CONTACT
            ):
                # Contact events can be particularly difficult to locate,
                # though a Sponsorship relation may hold a communicator's location.
                for member in event_cluster:
                    if relation_member[9] == member[9]:
                        affiliation_clusters.append(relation_cluster)
    member = event_cluster[0]  # we just need the event cluster info here
    # We want to prioritize LocatedNear relations
    if location_clusters:
        # TODO: a method for selecting a relation if there are more than two clusters
        # For now we're just grabbing the first relation cluster.
        for place_relation_member in location_clusters[0]:
            relation_predicate = place_relation_member[4].split("_")[-1]
            if relation_predicate == PLACE_PREDICATE:
                return _create_place_cluster(member, place_relation_member)
    if part_whole_clusters:
        place_filler = _get_place_from_clusters(member, part_whole_clusters)
        if place_filler:
            return place_filler
    if affiliation_clusters:
        place_filler = _get_place_from_clusters(member, affiliation_clusters)
        if place_filler:
            return place_filler
    # If no matching relation is found, see if a Place can
    # be extracted from an event argument.
    for member in event_cluster:
        for object_type in member[6]:
            if any(location_type in object_type for location_type in PLACE_TYPES):
                return _create_place_cluster(member, member)
    return None


def _get_higher_level_location(
    sublocation: Justification, location_map: Dict[Justification, Justification]
) -> Justification:
    """
    Use the location map to find the broadest reference to a place.
    """
    location = location_map.get(sublocation)
    return (
        _get_higher_level_location(location, location_map) if location else sublocation
    )


def _get_place_from_clusters(
    event_cluster_member: Cluster, relation_clusters: List[List[Cluster]]
) -> Optional[Cluster]:
    """
    Iterates through a list of relations containing an event argument
    and returns the first argument filler that is a "place" entity.
    If no qualifying entities are found, returns None.
    """
    for relation in relation_clusters:
        for relation_member in relation:
            for object_type in relation_member[6]:
                if any(loc_type in object_type for loc_type in PLACE_TYPES):
                    return _create_place_cluster(event_cluster_member, relation_member)
    return None


def _create_place_cluster(cluster_member: Cluster, relation_member: Cluster) -> Cluster:
    return (
        cluster_member[0],
        cluster_member[1],
        cluster_member[2],
        cluster_member[3],
        cluster_member[1] + "_" + PLACE_PREDICATE,
        relation_member[5],
        relation_member[6],
        relation_member[7],
        relation_member[8],
        relation_member[9],
    )


def _get_informative_justification(
    node: URIRef, graph: Graph
) -> Tuple[str, str, int, int]:
    """
    Grabs the informative justification for a given RDF node and returns relevant information

    Returns None if no informative justification field is found (This behavior could change at a
    later date).
    """
    informative_justification = graph.value(
        subject=node, predicate=AIDA_ANNOTATION.informativeJustification, any=False
    )
    if informative_justification is not None:
        span = (
            int(
                graph.value(
                    subject=informative_justification,
                    predicate=AIDA_ANNOTATION.startOffset,
                    any=False,
                )
            ),
            int(
                graph.value(
                    subject=informative_justification,
                    predicate=AIDA_ANNOTATION.endOffsetInclusive,
                    any=False,
                )
            ),
        )
        source = str(
            graph.value(
                subject=informative_justification,
                predicate=AIDA_ANNOTATION.source,
                any=False,
            )
        )

        source_doc = str(
            graph.value(
                subject=informative_justification,
                predicate=AIDA_ANNOTATION.sourceDocument,
                any=False,
            )
        )

        return (source, source_doc, *span)
    else:
        return ("", "", 0, 0)


def _get_informative_justification_link(
    db_path: Path,
    output_dir: Path,
    informative_justification: Tuple[str, str, int, int],
) -> Tuple[str, Path]:
    doc_dir = output_dir / "docs"
    doc_dir.mkdir(exist_ok=True)

    output_file, mention = render_html(
        db_path,
        doc_dir,
        informative_justification[1],
        informative_justification[2],
        informative_justification[3],
    )

    mention += f" ({informative_justification[2]}:{informative_justification[3]})"
    return mention, output_file.relative_to(output_dir)


def _entities_in_cluster(g: Graph, cluster: URIRef) -> ImmutableSet[URIRef]:
    return immutableset(
        flatten_once_to_list(
            g.objects(cluster_membership, AIDA_ANNOTATION.clusterMember)
            for cluster_membership in g.subjects(AIDA_ANNOTATION.cluster, cluster)
        )
    )


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
