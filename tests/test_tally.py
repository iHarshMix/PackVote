"""Unit tests for the ranked-choice (IRV) tally algorithm with deterministic tiebreakers."""
import pytest
from packvote.backend.core.tally import ranked_choice_tally


class TestBasicIRV:
    """Tests for standard IRV majority / elimination logic."""

    def test_clear_majority_first_round(self):
        """Candidate with > 50% first-choice votes wins immediately."""
        ballots = [
            ["Goa", "Coorg", "Kasol"],
            ["Goa", "Kasol", "Coorg"],
            ["Goa", "Coorg", "Kasol"],
            ["Coorg", "Goa", "Kasol"],
            ["Kasol", "Goa", "Coorg"],
        ]
        winner, counts = ranked_choice_tally(ballots)
        assert winner == "Goa"
        assert counts["Goa"] == 3
        assert counts["Coorg"] == 1
        assert counts["Kasol"] == 1

    def test_elimination_leads_to_majority(self):
        """No first-round majority; last-place elimination leads to a winner."""
        ballots = [
            ["Goa", "Coorg", "Kasol"],
            ["Goa", "Kasol", "Coorg"],
            ["Coorg", "Kasol", "Goa"],
            ["Coorg", "Goa", "Kasol"],
            ["Kasol", "Coorg", "Goa"],
        ]
        # First round: Goa=2, Coorg=2, Kasol=1 → Kasol eliminated
        # Second round: Goa=2, Coorg=3 (Kasol's vote goes to Coorg) → Coorg wins
        winner, counts = ranked_choice_tally(ballots)
        assert winner == "Coorg"
        # First-round counts preserved for display
        assert counts == {"Goa": 2, "Coorg": 2, "Kasol": 1}

    def test_single_ballot(self):
        """Single voter — their first choice wins."""
        ballots = [["Manali", "Goa", "Kasol"]]
        winner, counts = ranked_choice_tally(ballots)
        assert winner == "Manali"

    def test_two_candidates(self):
        """With two candidates, the one with more first-choice votes wins."""
        ballots = [
            ["Goa", "Kasol"],
            ["Goa", "Kasol"],
            ["Kasol", "Goa"],
        ]
        winner, counts = ranked_choice_tally(ballots)
        assert winner == "Goa"

    def test_unanimous(self):
        """All voters agree on the same first choice."""
        ballots = [
            ["Coorg", "Goa", "Kasol"],
            ["Coorg", "Kasol", "Goa"],
            ["Coorg", "Goa", "Kasol"],
        ]
        winner, counts = ranked_choice_tally(ballots)
        assert winner == "Coorg"
        assert counts["Coorg"] == 3


class TestTiebreakers:
    """Tests for the deterministic tiebreaker logic."""

    def test_tiebreak_by_budget(self):
        """When candidates tie, the one with lower budget wins."""
        ballots = [
            ["Goa", "Coorg"],
            ["Coorg", "Goa"],
        ]
        budget_estimates = {"Goa": 15000, "Coorg": 10000}
        winner, counts = ranked_choice_tally(ballots, budget_estimates=budget_estimates)
        assert winner == "Coorg"  # lower budget wins

    def test_tiebreak_by_swipes_when_budgets_equal(self):
        """When budgets are equal, the one with more swipe-rights wins."""
        ballots = [
            ["Goa", "Coorg"],
            ["Coorg", "Goa"],
        ]
        budget_estimates = {"Goa": 10000, "Coorg": 10000}
        swipe_counts = {"Goa": 5, "Coorg": 8}
        winner, counts = ranked_choice_tally(
            ballots,
            budget_estimates=budget_estimates,
            swipe_counts=swipe_counts,
        )
        assert winner == "Coorg"  # more swipes wins

    def test_tiebreak_alphabetical_fallback(self):
        """When budget and swipes are also equal, alphabetical order breaks the tie."""
        ballots = [
            ["Goa", "Kasol"],
            ["Kasol", "Goa"],
        ]
        budget_estimates = {"Goa": 10000, "Kasol": 10000}
        swipe_counts = {"Goa": 5, "Kasol": 5}
        winner, counts = ranked_choice_tally(
            ballots,
            budget_estimates=budget_estimates,
            swipe_counts=swipe_counts,
        )
        assert winner == "Goa"  # alphabetical: G < K

    def test_three_way_tie(self):
        """Three-way tie resolved by budget tiebreaker."""
        ballots = [
            ["Goa", "Coorg", "Kasol"],
            ["Coorg", "Kasol", "Goa"],
            ["Kasol", "Goa", "Coorg"],
        ]
        budget_estimates = {"Goa": 12000, "Coorg": 8000, "Kasol": 15000}
        winner, counts = ranked_choice_tally(ballots, budget_estimates=budget_estimates)
        assert winner == "Coorg"  # lowest budget


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_empty_ballots_raises(self):
        """Empty ballot list should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot tally zero ballots"):
            ranked_choice_tally([])

    def test_ballots_with_extra_candidates(self):
        """Ballots may reference candidates not on every ballot."""
        ballots = [
            ["Goa", "Manali"],
            ["Coorg", "Goa"],
            ["Goa", "Coorg"],
        ]
        winner, counts = ranked_choice_tally(ballots)
        assert winner == "Goa"  # 2 first-choice out of 3

    def test_no_tiebreak_data_defaults_gracefully(self):
        """Without budget/swipe data, tiebreaker falls through to alphabetical."""
        ballots = [
            ["Goa", "Coorg"],
            ["Coorg", "Goa"],
        ]
        winner, counts = ranked_choice_tally(ballots)
        # No budget or swipe data → alphabetical: Coorg < Goa
        assert winner == "Coorg"

    def test_elimination_with_tiebreak(self):
        """When two candidates tie for last place, the one with worse tiebreak is eliminated."""
        # 4 voters, 3 candidates: A=2, B=1, C=1
        # B and C tie for last — eliminate the one with worse tiebreak
        ballots = [
            ["Pondicherry", "Kasol", "Manali"],
            ["Pondicherry", "Manali", "Kasol"],
            ["Kasol", "Pondicherry", "Manali"],
            ["Manali", "Kasol", "Pondicherry"],
        ]
        budget_estimates = {"Pondicherry": 10000, "Kasol": 8000, "Manali": 15000}
        winner, counts = ranked_choice_tally(ballots, budget_estimates=budget_estimates)
        # Pondicherry has majority (2/4 > 50%? No, 2/4 = 50%, not >50%)
        # So elimination needed: Kasol=1, Manali=1 tied for last
        # Tiebreak: Kasol budget 8000 < Manali budget 15000 → Kasol is better → Manali eliminated
        # Manali's vote goes to Kasol (second choice)
        # Round 2: Pondicherry=2, Kasol=2 → still no majority
        # Now Pondicherry & Kasol tied. Tiebreak: Kasol budget 8000 < Pondicherry 10000 → Kasol wins
        assert winner == "Kasol"
