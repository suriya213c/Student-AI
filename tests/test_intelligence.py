"""Unit tests for the Student AI intelligence baseline."""

import unittest

from intelligence.concept_graph import ConceptGraph
from intelligence.learner_model import BayesianKnowledgeTracer
from intelligence.gap_diagnosis import diagnose_gaps
from intelligence.adaptive_policy import recommend_next_concept


class ConceptGraphTests(unittest.TestCase):
    def test_add_concept(self):
        graph = ConceptGraph()
        graph.add_concept("fractions", "Fractions")
        self.assertIn("fractions", graph.concepts())

    def test_prerequisite(self):
        graph = ConceptGraph()
        graph.add_prerequisite("algebra", "fractions")
        self.assertEqual(graph.prerequisites_for("algebra"), {"fractions"})

    def test_missing_prerequisite(self):
        graph = ConceptGraph()
        graph.add_prerequisite("algebra", "fractions")
        missing = graph.missing_prerequisites(
            "algebra", {"fractions": 0.2}, 0.6
        )
        self.assertEqual(missing, ["fractions"])


class LearnerModelTests(unittest.TestCase):
    def setUp(self):
        self.model = BayesianKnowledgeTracer()

    def test_initial_mastery(self):
        self.assertAlmostEqual(self.model.initial_mastery(), 0.2)

    def test_correct_answer_updates_mastery(self):
        self.assertGreater(self.model.update(0.4, True), 0.4)

    def test_incorrect_answer_still_allows_learning_transition(self):
        self.assertGreater(self.model.update(0.4, False), 0.0)

    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):
            BayesianKnowledgeTracer(p_init=1.5)


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.graph = ConceptGraph()
        self.graph.add_prerequisite("algebra", "fractions")

    def test_diagnoses_low_mastery(self):
        gaps = diagnose_gaps(
            self.graph, {"fractions": 0.2, "algebra": 0.3}
        )
        self.assertEqual(gaps[0]["concept_id"], "fractions")

    def test_recommends_available_prerequisite_first(self):
        choice = recommend_next_concept(
            self.graph, {"fractions": 0.2, "algebra": 0.1}
        )
        self.assertEqual(choice, "fractions")

    def test_empty_graph_returns_none(self):
        self.assertIsNone(recommend_next_concept(ConceptGraph(), {}))


if __name__ == "__main__":
    unittest.main()
