"""Identify concepts that may need more practice."""

def diagnose_gaps(graph, mastery_by_concept, threshold=0.6):
    gaps = []

    for concept_id in graph.concepts():
        mastery = float(mastery_by_concept.get(concept_id, 0.0))
        if mastery < threshold:
            gaps.append({
                "concept_id": concept_id,
                "mastery": mastery,
                "missing_prerequisites": graph.missing_prerequisites(
                    concept_id, mastery_by_concept, threshold
                ),
            })

    return sorted(gaps, key=lambda item: item["mastery"])
