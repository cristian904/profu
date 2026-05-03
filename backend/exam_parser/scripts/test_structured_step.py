"""
Standalone debug runner for the structured parsing step.

Run from repo root:
    uv run python backend/exam_parser/scripts/test_structured_step.py \
        --mode problems \
        --vision-input /absolute/path/to/vision.md \
        --model qwen2.5-coder:7b
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

# Allow running this script directly from repo root without PYTHONPATH tweaks.
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from exam_parser.parsers.ollama_structured import ollama_chat_text
from exam_parser.parsers.json_response_utils import parse_json_from_llm_response
from exam_parser.parsers.structured_models import ProblemsDocument, SolutionsDocument
from exam_parser.parsers.structured_normalize import (
    infer_subject_from_stem,
    normalize_solutions_output,
    validate_and_normalize_problems,
)
from exam_parser.parsers.structured_prompts import (
    EXTRACT_STRUCTURED_PROBLEMS_PROMPT,
    EXTRACT_STRUCTURED_SOLUTIONS_PROMPT,
)


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser for the standalone structured-step test runner."""
    parser = argparse.ArgumentParser(
        description=(
            "Test the structured extraction step outside pipeline: "
            "prompt + vision markdown + Ollama call."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("problems", "solutions"),
        required=True,
        help="Structured extraction mode.",
    )
    parser.add_argument(
        "--vision-input",
        type=Path,
        required=True,
        help="Path to vision markdown input file (Nougat output).",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL.",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5-coder:7b",
        help="Ollama model id.",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        help="Optional custom prompt file. If set, overrides built-in prompt.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print final prompt sent to Ollama.",
    )
    parser.add_argument(
        "--save-raw-output",
        type=Path,
        default=None,
        help="Optional path to save raw Ollama JSON output.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Also print parsed structured JSON output after markdown output.",
    )
    return parser


def resolve_prompt(mode: str, prompt_file: Path | None) -> str:
    """Resolve prompt from custom file or built-in constants."""
    if prompt_file is not None:
        print(f"[structured_debug] Loading custom prompt from: {prompt_file}")
        return prompt_file.read_text(encoding="utf-8")
    if mode == "problems":
        print("[structured_debug] Using built-in problems prompt")
        return EXTRACT_STRUCTURED_PROBLEMS_PROMPT
    print("[structured_debug] Using built-in solutions prompt")
    return EXTRACT_STRUCTURED_SOLUTIONS_PROMPT


def parse_structured_output_with_hint(
    mode: str,
    raw_output: str,
    inferred_subject: str | None = None,
) -> dict:
    """Parse JSON structured output with optional subject fallback hint."""
    data = parse_json_from_llm_response(raw_output)
    if not isinstance(data, dict):
        raise ValueError("Model output must be a JSON object")
    if mode == "problems":
        normalized = validate_and_normalize_problems(data, expected_key=inferred_subject)
        doc = ProblemsDocument.model_validate(normalized)
        return doc.to_exam_dict()
    if inferred_subject is not None:
        data = {inferred_subject: data.get(inferred_subject)} if isinstance(data.get(inferred_subject), list) else {}
    doc = SolutionsDocument.model_validate(normalize_solutions_output(data))
    return normalize_solutions_output(doc.to_solution_dict())


def print_raw_output(raw_output: str) -> None:
    """Print raw JSON output returned by Ollama."""
    print("\n===== STRUCTURED OUTPUT (RAW JSON) =====\n")
    print(raw_output)
    print("\n===== END =====")


def main() -> None:
    """Run standalone prompt + Ollama + parser flow and print structured output."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        if not args.vision_input.is_file():
            raise FileNotFoundError(f"Vision markdown file not found: {args.vision_input}")

        print(f"[structured_debug] Reading vision input: {args.vision_input}")
        vision_md = args.vision_input.read_text(encoding="utf-8")
        if not vision_md.strip():
            raise ValueError("Vision input markdown is empty")

        prompt_text = resolve_prompt(args.mode, args.prompt_file)
        hint_block = ""
        if args.mode == "problems":
            subject_hint = infer_subject_from_stem(args.vision_input.stem)
            if subject_hint is not None:
                hint_block = (
                    "\n\nSOURCE SUBJECT CONSTRAINT (from filename): "
                    f"{subject_hint}\n"
                    "You MUST use this exact subject key in output.\n"
                    f"- Include only key `{subject_hint}` at top level.\n"
                    "- Do not output other subject keys.\n"
                )
                print(
                    f"[structured_debug] Applied strict subject constraint from filename stem: "
                    f"{args.vision_input.stem} -> {subject_hint}"
                )
        full_prompt = prompt_text + hint_block + "\n---\n\n" + vision_md
        print(
            f"[structured_debug] Prompt prepared (chars={len(full_prompt)}), "
            f"mode={args.mode}, model={args.model}"
        )

        if args.print_prompt:
            print("\n===== PROMPT START =====\n")
            print(full_prompt)
            print("\n===== PROMPT END =====\n")

        print("[structured_debug] Sending request to Ollama...")
        raw_output = ollama_chat_text(
            base_url=args.base_url,
            model=args.model,
            user_content=full_prompt,
            request_json_format=True,
        )
        print(f"[structured_debug] Ollama response received (chars={len(raw_output)})")

        if args.save_raw_output is not None:
            args.save_raw_output.parent.mkdir(parents=True, exist_ok=True)
            args.save_raw_output.write_text(raw_output, encoding="utf-8")
            print(f"[structured_debug] Saved raw output to: {args.save_raw_output}")

        # Always print model output, even if strict parser validation fails next.
        print_raw_output(raw_output)

        print("[structured_debug] Parsing structured output...")
        parse_subject_hint = (
            infer_subject_from_stem(args.vision_input.stem)
            if args.mode == "problems"
            else None
        )
        structured_data = parse_structured_output_with_hint(
            args.mode,
            raw_output,
            inferred_subject=parse_subject_hint,
        )
        print("[structured_debug] Structured parse complete")

        if args.print_json:
            print("\n===== STRUCTURED OUTPUT (JSON) =====\n")
            print(json.dumps(structured_data, ensure_ascii=False, indent=2))
            print("\n===== END JSON =====")
    except Exception as exc:
        print(f"[structured_debug] ERROR: {exc}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
