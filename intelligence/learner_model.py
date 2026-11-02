"""Simple Bayesian Knowledge Tracing baseline."""

class BayesianKnowledgeTracer:
    def __init__(
        self,
        p_init=0.2,
        p_learn=0.15,
        p_guess=0.2,
        p_slip=0.1
    ):
        values = (p_init, p_learn, p_guess, p_slip)
        if any(not 0 <= value <= 1 for value in values):
            raise ValueError("All probabilities must be between 0 and 1")
        if p_guess + p_slip >= 1:
            raise ValueError("Guess plus slip must be less than 1")

        self.p_init = p_init
        self.p_learn = p_learn
        self.p_guess = p_guess
        self.p_slip = p_slip

    def update(self, mastery, correct):
        """Return updated mastery after one correct/incorrect answer."""
        prior = min(1.0, max(0.0, float(mastery)))

        if correct:
            numerator = prior * (1 - self.p_slip)
            denominator = numerator + (1 - prior) * self.p_guess
        else:
            numerator = prior * self.p_slip
            denominator = numerator + (1 - prior) * (1 - self.p_guess)

        posterior = numerator / denominator if denominator else prior
        learned = posterior + (1 - posterior) * self.p_learn
        return min(1.0, max(0.0, learned))

    def initial_mastery(self):
        return self.p_init
