"""Prerequisite graph for Student AI concepts."""

class ConceptGraph:
    def __init__(self):
        self._concepts = {}
        self._prerequisites = {}

    def add_concept(self, concept_id, title=None):
        if not concept_id:
            raise ValueError("concept_id cannot be empty")
        self._concepts[concept_id] = title or concept_id
        self._prerequisites.setdefault(concept_id, set())

    def add_prerequisite(self, concept_id, prerequisite_id):
        if concept_id == prerequisite_id:
            raise ValueError("A concept cannot depend on itself")
        self.add_concept(concept_id)
        self.add_concept(prerequisite_id)
        self._prerequisites[concept_id].add(prerequisite_id)

    def concepts(self):
        return list(self._concepts.keys())

    def prerequisites_for(self, concept_id):
        return set(self._prerequisites.get(concept_id, set()))

    def missing_prerequisites(self, concept_id, mastery, threshold=0.6):
        return sorted(
            item for item in self.prerequisites_for(concept_id)
            if float(mastery.get(item, 0.0)) < threshold
        )
