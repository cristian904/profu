"""
Simulari router.

Exposes endpoints for generating exam simulations and submitting self-scored results.
"""

from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator, model_validator

from profu_logging.feature_logger import get_feature_logger
from ai_backend.routers.common import get_supabase_client, get_user_id_from_request
from ai_backend.services.simulari.service import SimulationService
from ai_backend.common.exam_timestamps import format_exam_timestamp_for_db


router = APIRouter(prefix="/simulari", tags=["simulari"])

LOG_SIMULARI_API = get_feature_logger(source="simulari_api")


class GenerateSimulationRequest(BaseModel):
    """
    Request body for /simulari/generate endpoint.
    """

    school_subject: str = Field(
        default="mate",
        description="School subject for the simulation; DB catalog uses \"mate\" for merged Bac JSONs (default: mate). \"math\" is accepted and matches \"mate\" rows.",
    )

    @field_validator("school_subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        """
        Normalize and validate the school_subject field.
        """
        normalized = (value or "").strip().lower()
        if not normalized:
            raise ValueError("school_subject cannot be empty")
        return normalized


class GenerateSimulationResponse(BaseModel):
    """
    Response body for /simulari/generate endpoint.
    """

    simulation_id: int = Field(..., description="Identifier of the created exam_simulations row")
    school_subject: str = Field(..., description="School subject for the created simulation")


class ProblemScore(BaseModel):
    """
    Per-problem score payload for /simulari/scoring endpoint.
    """

    subject_number: int = Field(..., description="Subiect number (1, 2, or 3)")
    problem_number: int = Field(..., description="Problem number within the subiect")
    student_score: float = Field(..., description="Score given by the student for this problem")

    @field_validator("subject_number")
    @classmethod
    def validate_subject_number(cls, value: int) -> int:
        """
        Ensure subject_number is between 1 and 3.
        """
        if value not in (1, 2, 3):
            raise ValueError("subject_number must be 1, 2, or 3")
        return value

    @field_validator("problem_number")
    @classmethod
    def validate_problem_number(cls, value: int) -> int:
        """
        Ensure problem_number is positive.
        """
        if value <= 0:
            raise ValueError("problem_number must be positive")
        return value

    @field_validator("student_score")
    @classmethod
    def validate_student_score(cls, value: float) -> float:
        """
        Ensure score is non-negative.
        """
        if value < 0:
            raise ValueError("student_score must be >= 0")
        return value


class SimulationScoringRequest(BaseModel):
    """
    Request body for /simulari/scoring endpoint.

    Send either **problems** (per-subiect punctaje) or **total_score** alone after self-evaluation.
    If both are set, **problems** wins and **total_score** is ignored.
    """

    simulation_id: int = Field(..., description="Identifier of the simulation to score")
    problems: List[ProblemScore] = Field(
        default_factory=list,
        description="Per-problem scores (optional if total_score is sent)",
    )
    total_score: Optional[float] = Field(
        default=None,
        description="Single self-evaluated total (0–100) when not sending per-problem scores",
    )

    @model_validator(mode="after")
    def default_total_when_no_problems(self) -> "SimulationScoringRequest":
        """
        When [problems] is empty and [total_score] is omitted, treat total as 0 (legacy behaviour).
        """
        if self.problems:
            return self
        if self.total_score is None:
            return self.model_copy(update={"total_score": 0.0})
        return self

    @field_validator("total_score")
    @classmethod
    def validate_total_score_range(cls, value: Optional[float]) -> Optional[float]:
        """
        Clamp validation for optional total_score (Bac-style scale 0–100).
        """
        if value is None:
            return value
        if value < 0:
            raise ValueError("total_score must be >= 0")
        if value > 100:
            raise ValueError("total_score must be <= 100")
        return value


class SimulationScoringResponse(BaseModel):
    """
    Response body for /simulari/scoring endpoint.
    """

    simulation_id: int = Field(..., description="Identifier of the scored simulation")
    total_score: float = Field(..., description="Total score after aggregation of per-problem scores")


def _get_simulation_service(supabase: Any) -> SimulationService:
    """
    Factory for SimulationService with error handling around Supabase configuration.
    """
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured on the server",
        )
    return SimulationService(supabase_client=supabase)


@router.post(
    "/generate",
    response_model=GenerateSimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_simulation(
    request: Request,
    body: GenerateSimulationRequest,
    supabase: Any = Depends(get_supabase_client),
) -> GenerateSimulationResponse:
    """
    Generate a new simulation for the authenticated user.

    The endpoint returns only the simulation_id. The UI is responsible for
    fetching the full exam content from Supabase using this id.
    """
    user_id: UUID = get_user_id_from_request(request)
    LOG_SIMULARI_API.info(
        f"Generate simulation requested for subject={body.school_subject}",
        user_id=user_id,
    )
    service = _get_simulation_service(supabase=supabase)

    try:
        simulation_id = service.create_simulation(
            auth_user_id=user_id,
            school_subject=body.school_subject,
        )
    except ValueError as exc:
        LOG_SIMULARI_API.error(
            error=exc,
            user_id=user_id,
            traceback=None,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        LOG_SIMULARI_API.error(
            error=exc,
            user_id=user_id,
            traceback=None,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create simulation",
        ) from exc

    return GenerateSimulationResponse(
        simulation_id=simulation_id,
        school_subject=body.school_subject,
    )


@router.post(
    "/scoring",
    response_model=SimulationScoringResponse,
)
async def submit_simulation_scoring(
    request: Request,
    body: SimulationScoringRequest,
    supabase: Any = Depends(get_supabase_client),
) -> SimulationScoringResponse:
    """
    Submit self-scored results for a simulation.

    This endpoint:
    - validates that the simulation belongs to the current user
    - updates per-problem scores in exam_simulation_problems
    - computes and persists the total score on exam_simulations
    """
    user_id: UUID = get_user_id_from_request(request)
    LOG_SIMULARI_API.info(
        f"Scoring submitted for simulation_id={body.simulation_id} "
        f"problems={len(body.problems)} total_only={body.total_score is not None and not body.problems}",
        user_id=user_id,
    )
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured on the server",
        )

    # Step 1: verify simulation belongs to the user
    sim_resp = (
        supabase.table("exam_simulations")
        .select("id, auth_user_id")
        .eq("id", body.simulation_id)
        .limit(1)
        .execute()
    )
    sim_rows = getattr(sim_resp, "data", None) or []
    if not sim_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )
    sim_row = sim_rows[0]
    owner_id = sim_row.get("auth_user_id")
    if str(owner_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to score this simulation",
        )

    # Step 2: update per-problem scores, or accept a single self-evaluated total
    total_score: float = 0.0
    if body.problems:
        for problem in body.problems:
            update_resp = (
                supabase.table("exam_simulation_problems")
                .update({"student_score": problem.student_score})
                .eq("exam_simulation_id", body.simulation_id)
                .eq("subject_number", problem.subject_number)
                .eq("problem_number", problem.problem_number)
                .execute()
            )
            updated_rows = getattr(update_resp, "data", None) or []
            if not updated_rows:
                LOG_SIMULARI_API.warning(
                    (
                        "No matching exam_simulation_problems row when scoring "
                        f"simulation_id={body.simulation_id}, subiect={problem.subject_number}, "
                        f"problema={problem.problem_number}"
                    ),
                    user_id=user_id,
                )
                continue
            total_score += float(problem.student_score)
    else:
        total_score = float(body.total_score) if body.total_score is not None else 0.0
        LOG_SIMULARI_API.info(
            f"Applying self-evaluated total_score={total_score} for simulation_id={body.simulation_id}",
            user_id=user_id,
        )

    # Step 3: persist total score and finished_at (YYYY-MM-DD HH:MM:SS, Europe/Bucharest)
    finished_str = format_exam_timestamp_for_db()
    LOG_SIMULARI_API.info(
        f"exam_simulations.finished_at for id={body.simulation_id} set to {finished_str}",
        user_id=user_id,
    )
    _ = (
        supabase.table("exam_simulations")
        .update(
            {
                "student_score": round(total_score, 2),
                "finished_at": finished_str,
            },
        )
        .eq("id", body.simulation_id)
        .execute()
    )

    LOG_SIMULARI_API.info(
        f"Simulation {body.simulation_id} scored with total={total_score}",
        user_id=user_id,
    )
    return SimulationScoringResponse(
        simulation_id=body.simulation_id,
        total_score=round(total_score, 2),
    )

