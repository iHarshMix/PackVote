"""
Ranked-choice (Instant Runoff Voting) tally with deterministic tiebreakers.

IRV Algorithm:
1. Count first-choice votes for each candidate.
2. If any candidate has > 50% of total votes, they win.
3. Otherwise, eliminate the candidate with the fewest first-choice votes.
4. Redistribute their ballots to each voter's next-ranked candidate.
5. Repeat until a majority winner emerges or one candidate remains.

Tiebreaker (when two candidates tie for elimination or final winner):
1. Lowest budget_estimate from the recommendations table wins.
2. If budgets are equal, highest swipe-right count wins.
3. If still tied, alphabetical order (deterministic fallback).
"""
import logging
from collections import Counter

logger = logging.getLogger(__name__)


def ranked_choice_tally(
    ballots: list[list[str]],
    budget_estimates: dict[str, int] | None = None,
    swipe_counts: dict[str, int] | None = None,
) -> tuple[str, dict[str, int]]:
    """
    Run instant-runoff voting on a list of ranked ballots.

    Args:
        ballots: List of ranked lists, e.g. [["Goa", "Coorg", "Kasol"], ...]
        budget_estimates: Optional mapping of destination -> budget estimate (lower is better for tiebreak).
        swipe_counts: Optional mapping of destination -> total swipe-right count (higher is better for tiebreak).

    Returns:
        Tuple of (winner_name, first_choice_vote_counts_dict).
        The vote_counts dict reflects the first-round distribution for display purposes.
    """
    if not ballots:
        raise ValueError("Cannot tally zero ballots")

    budget_estimates = budget_estimates or {}
    swipe_counts = swipe_counts or {}

    # Build initial candidate set from all ballots
    candidates = set()
    for ballot in ballots:
        for c in ballot:
            candidates.add(c)

    if not candidates:
        raise ValueError("No candidates found in ballots")

    # Capture first-round counts for display purposes
    first_round_counts = _count_first_choices(ballots, candidates)

    # IRV elimination loop
    active_candidates = set(candidates)

    while True:
        counts = _count_first_choices(ballots, active_candidates)
        total = sum(counts.values())

        if total == 0:
            # Edge case: no valid votes remaining (all ballots exhausted)
            # Pick winner from remaining candidates via tiebreak
            winner = _tiebreak_pick(list(active_candidates), budget_estimates, swipe_counts)
            return winner, first_round_counts

        # Check for majority winner
        for candidate, count in counts.items():
            if count > total / 2:
                return candidate, first_round_counts

        # Find candidate(s) with fewest votes for elimination
        min_count = min(counts.values())
        last_place = [c for c, v in counts.items() if v == min_count]

        if len(last_place) == len(active_candidates):
            # Everyone is tied — use tiebreak to pick the winner
            winner = _tiebreak_pick(list(active_candidates), budget_estimates, swipe_counts)
            return winner, first_round_counts

        if len(last_place) > 1:
            # Multiple candidates tied for last — eliminate the one that loses the tiebreak
            # (i.e., the one with worst tiebreak ranking)
            to_eliminate = _tiebreak_eliminate(last_place, budget_estimates, swipe_counts)
        else:
            to_eliminate = last_place[0]

        active_candidates.remove(to_eliminate)
        logger.info(f"IRV: Eliminated '{to_eliminate}' (had {counts.get(to_eliminate, 0)} votes). "
                     f"Remaining: {active_candidates}")

        if len(active_candidates) == 1:
            winner = active_candidates.pop()
            return winner, first_round_counts

        if len(active_candidates) == 0:
            # Shouldn't happen, but safety fallback
            raise ValueError("All candidates eliminated — impossible state")


def _count_first_choices(ballots: list[list[str]], active_candidates: set[str]) -> dict[str, int]:
    """Count first-choice votes, skipping eliminated candidates."""
    counts: dict[str, int] = {c: 0 for c in active_candidates}
    for ballot in ballots:
        for choice in ballot:
            if choice in active_candidates:
                counts[choice] += 1
                break  # only count first active choice
    return counts


def _tiebreak_sort_key(candidate: str,
                       budget_estimates: dict[str, int],
                       swipe_counts: dict[str, int]) -> tuple:
    """
    Sort key for tiebreaking. Lower key = better candidate.
    Priority: (lower budget, higher swipes inverted, alphabetical name).
    """
    budget = budget_estimates.get(candidate, float('inf'))
    swipes = swipe_counts.get(candidate, 0)
    return (budget, -swipes, candidate)


def _tiebreak_pick(candidates: list[str],
                   budget_estimates: dict[str, int],
                   swipe_counts: dict[str, int]) -> str:
    """Pick the best candidate from a tied set (winner selection)."""
    candidates.sort(key=lambda c: _tiebreak_sort_key(c, budget_estimates, swipe_counts))
    return candidates[0]


def _tiebreak_eliminate(candidates: list[str],
                        budget_estimates: dict[str, int],
                        swipe_counts: dict[str, int]) -> str:
    """Pick the worst candidate from a tied set (elimination selection)."""
    candidates.sort(key=lambda c: _tiebreak_sort_key(c, budget_estimates, swipe_counts))
    return candidates[-1]  # worst tiebreak = last in sorted order

