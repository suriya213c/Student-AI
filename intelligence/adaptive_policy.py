"""Recommend the next concept to study."""

def recommend_next_concept(graph, mastery_by_concept, threshold=0.6):
    concepts = graph.concepts()

    eligible = [
        concept_id for concept_id in concepts
        if float(mastery_by_concept.get(concept_id, 0.0)) < threshold
        and not graph.missing_prerequisites(
            concept_id, mastery_by_concept, threshold
        )
    ]

    if eligible:
        return min(
            eligible,
            key=lambda item: float(mastery_by_concept.get(item, 0.0))
        )

    if concepts:
        return min(
            concepts,
            key=lambda item: float(mastery_by_concept.get(item, 0.0))
        )

    return None
