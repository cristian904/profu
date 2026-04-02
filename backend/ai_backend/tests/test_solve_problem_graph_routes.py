"""Unit tests for solve_problem graph routing helpers."""

from ai_backend.services.solve_problem.graph import (
    ProblemSolvingState,
    route_after_intent,
    route_after_progress_eval,
    route_after_progress_intent,
)


def _state(intent: str = "") -> ProblemSolvingState:
    """Minimal valid state for routing functions (only ``intent`` is read)."""
    return {
        "messages": [],
        "problem_text": "",
        "intent": intent,
        "student_work": "",
        "hint_level": 0,
        "full_solution_requested": False,
    }


class TestRouteAfterIntent:
    def test_initial_question(self) -> None:
        assert route_after_intent(_state(intent="initial_question")) == "provide_hint"

    def test_solve(self) -> None:
        assert route_after_intent(_state(intent="solve")) == "provide_solution"

    def test_progress(self) -> None:
        assert route_after_intent(_state(intent="progress")) == "evaluate_progress"

    def test_default_new_hint(self) -> None:
        assert route_after_intent(_state(intent="new_hint")) == "provide_hint"
        # Missing intent key: route uses default "new_hint" -> provide_hint
        minimal: ProblemSolvingState = {
            "messages": [],
            "problem_text": "",
            "intent": "",
            "student_work": "",
            "hint_level": 0,
            "full_solution_requested": False,
        }
        del minimal["intent"]  # type: ignore[misc]
        assert route_after_intent(minimal) == "provide_hint"


class TestRouteAfterProgress:
    def test_eval_always_detect_intent(self) -> None:
        assert route_after_progress_eval(_state()) == "detect_progress_intent"

    def test_intent_bad_explains(self) -> None:
        assert route_after_progress_intent(_state(intent="bad")) == "explain_error"

    def test_intent_good_hint(self) -> None:
        assert route_after_progress_intent(_state(intent="good")) == "provide_hint"
