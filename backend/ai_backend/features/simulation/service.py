"""
Simulation service: generate exam simulations from `exam_problems` and persist
to `exam_simulations` / `exam_simulation_problems`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import UUID

from supabase import Client

from ai_backend.logging.feature_logger import get_feature_logger
from ai_backend.utils.exam_timestamps import format_exam_timestamp_for_db


LOG_SIMULARI = get_feature_logger(source="simulari")


def _school_subject_db_values(school_subject: str) -> List[str]:
    """
    Map API/UI subject labels to values stored in exam_problems.school_subject.

    Merged exam JSONs use Romanian labels (e.g. \"mate\"); clients may send \"math\".
    Returns a deduplicated list for PostgREST `in` filters.
    """
    key = (school_subject or "").strip().lower()
    if not key:
        return []
    variants: List[str] = [key]
    # Romanian Bac data in DB typically uses \"mate\" (see load_merged_to_db merged JSON).
    if key == "math":
        if "mate" not in variants:
            variants.append("mate")
    elif key == "mate":
        if "math" not in variants:
            variants.append("math")
    return variants


@dataclass(frozen=True)
class SelectedProblem:
    """
    Represents one selected problem for a simulation.
    """

    exam_problem_id: int
    subject_number: int
    problem_number: int
    order_index: int


class SimulationService:
    """
    Service responsible for generating exam simulations.

    Centralizes:
    - choosing problems from `exam_problems`
    - inserting rows into `exam_simulations` and `exam_simulation_problems`
    """

    def __init__(self, supabase_client: Client) -> None:
        """
        Initialize the service with a Supabase client.
        """
        self._supabase = supabase_client

    def _fetch_candidates(
        self,
        school_subject: str,
        subject_number: int,
        problem_number: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch candidate exam problems for a given (subject_number, problem_number, subject).

        Returns a list of rows from `exam_problems`. If the list is empty, the caller
        must decide how to handle the absence of candidates.
        """
        subject_values = _school_subject_db_values(school_subject)
        if not subject_values:
            LOG_SIMULARI.warning(
                f"Empty school_subject after normalization: input={school_subject!r}",
                user_id=None,
            )
            return []

        LOG_SIMULARI.info(
            (
                f"Fetching exam_problems for school_subject in {subject_values}, "
                f"subiect={subject_number}, problema={problem_number}"
            ),
            user_id=None,
        )
        response = (
            self._supabase.table("exam_problems")
            .select("id, subject_number, problem_number, school_subject")
            .in_("school_subject", subject_values)
            .eq("subject_number", subject_number)
            .eq("problem_number", problem_number)
            .execute()
        )
        data = getattr(response, "data", None) or []
        LOG_SIMULARI.info(
            (
                f"Found {len(data)} candidates for school_subject in {subject_values}, "
                f"subiect={subject_number}, problema={problem_number}"
            ),
            user_id=None,
        )
        return data

    def _choose_one_candidate(
        self,
        candidates: List[Dict[str, Any]],
        subject_number: int,
        problem_number: int,
    ) -> Dict[str, Any]:
        """
        Choose one candidate from a non-empty list (random when multiple exist).
        """
        if not candidates:
            raise ValueError(
                "No exam problem available for "
                f"subject_number={subject_number}, problem_number={problem_number}. "
                "Check exam_problems has rows for this slot and that school_subject "
                "matches (DB often uses \"mate\"; \"math\" is accepted as an alias).",
            )
        chosen = random.choice(candidates)
        LOG_SIMULARI.info(
            (
                "Chosen exam_problem_id="
                f"{chosen.get('id')} for subiect={subject_number}, problema={problem_number}"
            ),
            user_id=None,
        )
        return chosen

    def _build_simulation_blueprint(
        self,
        school_subject: str,
    ) -> List[SelectedProblem]:
        """
        Build the list of problems that should be included in a simulation.

        Bac structure:
        - Subiectul I: 6 problems (1..6), 5p each
        - Subiectul II: 2 problems (1..2), 15p each
        - Subiectul III: 2 problems (1..2), 15p each
        """
        selected: List[SelectedProblem] = []
        order_index: int = 1

        for problem_number in range(1, 7):
            candidates = self._fetch_candidates(
                school_subject=school_subject,
                subject_number=1,
                problem_number=problem_number,
            )
            chosen = self._choose_one_candidate(
                candidates=candidates,
                subject_number=1,
                problem_number=problem_number,
            )
            selected.append(
                SelectedProblem(
                    exam_problem_id=int(chosen["id"]),
                    subject_number=1,
                    problem_number=problem_number,
                    order_index=order_index,
                ),
            )
            order_index += 1

        for problem_number in range(1, 3):
            candidates = self._fetch_candidates(
                school_subject=school_subject,
                subject_number=2,
                problem_number=problem_number,
            )
            chosen = self._choose_one_candidate(
                candidates=candidates,
                subject_number=2,
                problem_number=problem_number,
            )
            selected.append(
                SelectedProblem(
                    exam_problem_id=int(chosen["id"]),
                    subject_number=2,
                    problem_number=problem_number,
                    order_index=order_index,
                ),
            )
            order_index += 1

        for problem_number in range(1, 3):
            candidates = self._fetch_candidates(
                school_subject=school_subject,
                subject_number=3,
                problem_number=problem_number,
            )
            chosen = self._choose_one_candidate(
                candidates=candidates,
                subject_number=3,
                problem_number=problem_number,
            )
            selected.append(
                SelectedProblem(
                    exam_problem_id=int(chosen["id"]),
                    subject_number=3,
                    problem_number=problem_number,
                    order_index=order_index,
                ),
            )
            order_index += 1

        LOG_SIMULARI.info(
            f"Simulation blueprint built with {len(selected)} problems",
            user_id=None,
        )
        return selected

    def create_simulation(
        self,
        auth_user_id: UUID,
        school_subject: str = "mate",
    ) -> int:
        """
        Create a new simulation for the given user and return its id.

        Returns:
            The id of the created exam_simulations row.
        """
        LOG_SIMULARI.info(
            f"Creating new simulation for user={auth_user_id} subject={school_subject}",
            user_id=auth_user_id,
        )

        try:
            blueprint = self._build_simulation_blueprint(school_subject=school_subject)
        except ValueError as exc:
            LOG_SIMULARI.error(
                error=exc,
                user_id=auth_user_id,
                traceback=None,
            )
            raise

        started_str = format_exam_timestamp_for_db()
        LOG_SIMULARI.info(
            f"exam_simulations.started_at will be set to {started_str}",
            user_id=auth_user_id,
        )
        sim_payload: Dict[str, Any] = {
            "auth_user_id": str(auth_user_id),
            "school_subject": school_subject,
            "started_at": started_str,
        }
        # postgrest 2.x: insert() returns SyncQueryRequestBuilder (execute only; no .select() after insert).
        sim_resp = (
            self._supabase.table("exam_simulations")
            .insert(sim_payload)
            .execute()
        )
        sim_rows = getattr(sim_resp, "data", None) or []
        if not sim_rows:
            raise RuntimeError("Failed to insert exam_simulations row")
        simulation_id = int(sim_rows[0]["id"])
        LOG_SIMULARI.info(
            f"Created exam_simulations row id={simulation_id}",
            user_id=auth_user_id,
        )

        problems_payload: List[Dict[str, Any]] = []
        for problem in blueprint:
            problems_payload.append(
                {
                    "exam_simulation_id": simulation_id,
                    "exam_problem_id": problem.exam_problem_id,
                    "order_index": problem.order_index,
                    "subject_number": problem.subject_number,
                    "problem_number": problem.problem_number,
                },
            )

        LOG_SIMULARI.info(
            f"Inserting {len(problems_payload)} rows into exam_simulation_problems",
            user_id=auth_user_id,
        )
        _ = (
            self._supabase.table("exam_simulation_problems")
            .insert(problems_payload)
            .execute()
        )

        LOG_SIMULARI.info(
            f"Simulation {simulation_id} created successfully",
            user_id=auth_user_id,
        )
        return simulation_id
