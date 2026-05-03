"""
Parse and serialize structured exam artifacts as Markdown + fenced YAML blocks.

LaTeX-heavy fields use YAML literal scalars (``|``) so backslashes are preserved.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

import yaml

from exam_parser.parsers.structured_models import (
    ItemSolutionBlock,
    MergedDocument,
    MergedS1Record,
    MergedS23Record,
    ProblemRecord,
    ProblemsDocument,
    SolutionS1Record,
    SolutionS23Record,
    SolutionsDocument,
    SolutionStep,
)

logger = logging.getLogger(__name__)


def normalize_llm_markdown_response(text: str) -> str:
    """
    Strip leading/trailing whitespace and optional outer markdown code fence.

    Models sometimes wrap the full document in ```markdown ... ```.
    """
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if not lines:
        return t
    first = lines[0].strip()
    if not first.startswith("```"):
        return t
    lines = lines[1:]
    while lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


FORMAT_PROBLEMS = "exam-parser-structured-problems-v1"
FORMAT_SOLUTIONS = "exam-parser-structured-solutions-v1"
FORMAT_MERGED = "exam-parser-structured-merged-v1"

# "##" / "###" + Subject or Romanian Subiect (LLM heading depth varies).
SUBJECT_SECTION_RE = re.compile(
    r"^#{2,3}\s*(?:Subject|Subiect)\s+(s[123])\s*$",
    re.IGNORECASE | re.MULTILINE,
)
PROBLEM_HEADING_RE = re.compile(r"^#{2,4}\s*Problem\s*$", re.IGNORECASE | re.MULTILINE)
PROBLEM_NUMBER_HEADING_RE = re.compile(r"^#{2,4}\s*Problem\s+(\d+)\s*$", re.IGNORECASE | re.MULTILINE)
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Opening fence: ```yaml, ```YAML, ``` yml, etc.
_YAML_FENCE_OPEN_RE = re.compile(r"^```\s*(yaml|yml)\s*$", re.IGNORECASE)


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """
    Strip optional YAML front matter; return (meta dict, body).

    On parse errors, logs and returns empty meta with original text.
    """
    m = FRONT_MATTER_RE.match(text.strip())
    if not m:
        return {}, text
    raw_fm = m.group(1)
    body = text.strip()[m.end() :]
    try:
        loaded = yaml.safe_load(raw_fm)
        if isinstance(loaded, dict):
            return loaded, body
        logger.warning("Front matter is not a mapping; ignoring")
        return {}, text.strip()
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse front matter YAML: %s", exc)
        return {}, text.strip()


def _is_yaml_fence_opener(line: str) -> bool:
    """True if the line opens a YAML code fence (language tag yaml or yml)."""
    return bool(_YAML_FENCE_OPEN_RE.match(line.strip()))


def _is_fence_closer(line: str) -> bool:
    """
    True if the line closes a markdown code fence.

    Models sometimes repeat the language on the closing line (`` ```yaml ``) or
    use `` ```markdown ``; a plain `` ``` `` is the canonical closer.
    """
    s = line.strip()
    if not s.startswith("```"):
        return False
    rest = s[3:].strip().lower()
    if rest == "":
        return True
    if rest in ("yaml", "yml", "markdown", "md"):
        return True
    return False


def _try_parse_merged_plain_fence(inner: str) -> dict[str, Any] | None:
    """Bare ``` fence holding a merged problem YAML (statement + solution field)."""
    inner_stripped = inner.strip()
    if not inner_stripped or inner_stripped.startswith("{"):
        return None
    try:
        data = yaml.safe_load(inner)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    if "statement" not in data or "number" not in data:
        return None
    if "solution_steps" not in data and "item_solutions" not in data:
        return None
    return data


def _try_parse_solution_plain_fence(inner: str) -> dict[str, Any] | None:
    """Detect bare ``` fences that hold a solution YAML object."""
    inner_stripped = inner.strip()
    if not inner_stripped or inner_stripped.startswith("{"):
        return None
    try:
        data = yaml.safe_load(inner)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    if "solution_steps" not in data and "item_solutions" not in data:
        return None
    return data


def _try_parse_problem_yaml_block(inner: str, *, context: str) -> dict[str, Any] | None:
    """
    If *inner* is YAML mapping with problem-like keys, return the dict; else None.

    Used for unlabeled ``` fences that models sometimes emit instead of ```yaml.
    """
    inner_stripped = inner.strip()
    if not inner_stripped or inner_stripped.startswith("{"):
        return None
    try:
        data = yaml.safe_load(inner)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    if "statement" not in data and "number" not in data:
        return None
    return data


def _default_problem_plain_predicate(inner: str) -> dict[str, Any] | None:
    """Default checker for unlabeled ``` fences in problem documents."""
    return _try_parse_problem_yaml_block(inner, context="plain fence")


def _iter_yaml_fence_bodies(
    chunk: str,
    *,
    allow_plain_fence: bool = False,
    plain_fence_predicate: Callable[[str], dict[str, Any] | None] | None = None,
) -> list[str]:
    """
    Extract inner text of each YAML code fence in order.

    Accepts ```yaml / ```yml with any casing/spacing. Optionally treats a plain
    ``` fence as YAML when *plain_fence_predicate* accepts the inner text
    (defaults to problem-shaped YAML when *allow_plain_fence* is True).
    """
    predicate: Callable[[str], dict[str, Any] | None] | None = plain_fence_predicate
    if allow_plain_fence and predicate is None:
        predicate = _default_problem_plain_predicate

    lines = chunk.splitlines()
    blocks: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()
        if _is_yaml_fence_opener(stripped):
            i += 1
            chunk_lines: list[str] = []
            while i < n and not _is_fence_closer(lines[i]):
                chunk_lines.append(lines[i])
                i += 1
            inner = "\n".join(chunk_lines)
            if i >= n:
                if inner.strip():
                    logger.warning(
                        "Unclosed ```yaml fence (end of input); using %d characters as one block",
                        len(inner),
                    )
                    blocks.append(inner)
                else:
                    raise ValueError(
                        "Unclosed ```yaml fence in structured markdown (empty body before end of input)"
                    )
                continue
            blocks.append(inner)
            i += 1
            continue
        if allow_plain_fence and predicate is not None and re.match(r"^```\s*$", stripped):
            i += 1
            chunk_lines = []
            while i < n and not _is_fence_closer(lines[i]):
                chunk_lines.append(lines[i])
                i += 1
            inner = "\n".join(chunk_lines)
            if i >= n:
                if inner.strip():
                    logger.warning(
                        "Unclosed plain ``` fence (end of input); using %d characters as one block",
                        len(inner),
                    )
                    blocks.append(inner)
                else:
                    raise ValueError(
                        "Unclosed ``` fence in structured markdown (empty body before end of input)"
                    )
                continue
            if predicate(inner) is not None:
                blocks.append(inner)
            i += 1
            continue
        i += 1
    return blocks


def _iter_unfenced_problem_yaml_bodies(section_text: str) -> list[str]:
    """
    Extract YAML-like bodies under ``## Problem`` headings when fences are missing.

    Some model responses keep valid mapping content but omit `````yaml`` fences.
    This fallback scans each Problem chunk and keeps only chunks that look like
    problem mappings (e.g. include ``number``/``statement`` keys).
    """
    matches = list(PROBLEM_HEADING_RE.finditer(section_text))
    if not matches:
        return []

    candidates: list[str] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_text)
        chunk = section_text[start:end].strip()
        if not chunk:
            continue
        if _try_parse_problem_yaml_block(chunk, context="unfenced problem chunk") is not None:
            candidates.append(chunk)
    return candidates


def _extract_heading_value(block: str, heading: str) -> str | None:
    """Extract text under a ``### <heading>:`` style section until next heading."""
    inline_pattern = re.compile(
        rf"^#{{3,4}}\s*{re.escape(heading)}\s*:[ \t]*(?P<value>.+?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    inline_match = inline_pattern.search(block)
    if inline_match:
        value = inline_match.group("value").strip()
        return value if value else None

    pattern = re.compile(
        rf"^#{{3,4}}\s*{re.escape(heading)}\s*:?\s*$\n(?P<body>.*?)(?=^#{{3,4}}\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(block)
    if not match:
        return None
    value = match.group("body").strip()
    return value if value else None


def _parse_problems_from_problem_heading_sections(section_text: str) -> list[dict[str, Any]]:
    """
    Parse fallback problem blocks from ``## Problem <N>`` + ``###`` subsections.

    Expected keys in each problem block:
    - Statement
    Optional:
    - Topic
    - Difficulty
    - Items (as markdown bullet list)
    """
    matches = list(PROBLEM_NUMBER_HEADING_RE.finditer(section_text))
    if not matches:
        return []

    records: list[dict[str, Any]] = []
    for idx, match in enumerate(matches):
        number = int(match.group(1))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_text)
        block = section_text[start:end]

        statement = _extract_heading_value(block, "Statement")
        items_raw = _extract_heading_value(block, "Items")

        if statement is None:
            continue

        items: list[str] = []
        if items_raw:
            for line in items_raw.splitlines():
                stripped = line.strip()
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip())
                elif stripped.startswith("* "):
                    items.append(stripped[2:].strip())

        records.append(
            {
                "number": number,
                "statement": statement,
                "items": items,
            }
        )
    return records


# Typical mapping keys at column 0 — do not indent in the broad repair pass.
_REPAIR_KNOWN_KEY = re.compile(
    r"^(?:number|item|item_solutions|solution_steps|subject|statement|format|items|"
    r"score|step)\s*:",
    re.IGNORECASE,
)
# Any ``word:`` at column 0 (YAML key).
_COL0_YAML_KEY = re.compile(r"^[A-Za-z_][\w_]*\s*:\s")


def _repair_yaml_latex_loose_lines(block: str) -> str:
    """
    Indent column-0 lines that start with ``\\`` (common inside ``step: |`` LaTeX).
    """
    lines = block.splitlines()
    out: list[str] = []
    indent = "      "
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            out.append(line)
            continue
        if line[0] in " \t#":
            out.append(line)
            continue
        if stripped.startswith("\\"):
            out.append(indent + line)
            continue
        out.append(line)
    return "\n".join(out)


def _repair_yaml_loose_continuation_lines(block: str) -> str:
    """
    Indent any column-0 line that is not a YAML key, list marker, or document marker.

    Catches Romanian text and math without a leading backslash after ``step: |``.
    """
    lines = block.splitlines()
    out: list[str] = []
    indent = "      "
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            out.append(line)
            continue
        if line[0] in " \t#":
            out.append(line)
            continue
        if stripped in ("---", "..."):
            out.append(line)
            continue
        if stripped.startswith("- "):
            out.append(line)
            continue
        if _REPAIR_KNOWN_KEY.match(stripped) or _COL0_YAML_KEY.match(stripped):
            out.append(line)
            continue
        out.append(indent + line)
    return "\n".join(out)


def _safe_load_yaml_block(block: str, *, context: str) -> dict[str, Any]:
    """Parse one YAML document; must be a mapping."""
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as first_exc:
        for repair_fn, label in (
            (_repair_yaml_latex_loose_lines, "latex loose lines"),
            (_repair_yaml_loose_continuation_lines, "column-0 continuation lines"),
        ):
            repaired = repair_fn(block)
            if repaired == block:
                continue
            try:
                data = yaml.safe_load(repaired)
            except yaml.YAMLError:
                continue
            logger.warning(
                "YAML block in %s was auto-repaired (%s); use indented lines under `step: |` in prompts",
                context,
                label,
            )
            break
        else:
            raise ValueError(f"Invalid YAML in {context}: {first_exc}") from first_exc
    if data is None:
        raise ValueError(f"Empty YAML block in {context}")
    if not isinstance(data, dict):
        raise ValueError(f"YAML block in {context} must be a mapping, got {type(data).__name__}")
    return data


def _subject_from_meta(meta: dict[str, Any]) -> str | None:
    """
    Single subject from YAML front matter: ``subject`` / ``Subject`` / ``subiect``,
    or ``subjects: [s1]`` with exactly one entry.
    """
    if not isinstance(meta, dict):
        return None
    for key, val in meta.items():
        if not isinstance(key, str):
            continue
        if key.lower() in ("subject", "subiect") and isinstance(val, str):
            v = val.strip().lower()
            if v in ("s1", "s2", "s3"):
                return v
    subs = meta.get("subjects")
    if not isinstance(subs, list):
        subs = meta.get("Subjects")
    if isinstance(subs, list) and len(subs) == 1:
        only = subs[0]
        if isinstance(only, str) and only.lower() in ("s1", "s2", "s3"):
            return only.lower()
    return None


def _split_subject_sections(body: str) -> list[tuple[str, str]]:
    """Split body by '## Subject sN' headings. Returns [(s1|s2|s3, section_text), ...]."""
    matches = list(SUBJECT_SECTION_RE.finditer(body))
    if not matches:
        return []
    out: list[tuple[str, str]] = []
    for idx, m in enumerate(matches):
        subj = m.group(1).lower()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        out.append((subj, body[start:end]))
    return out


def _subject_from_front_or_body(meta: dict[str, Any], body: str) -> str | None:
    """Resolve subject key s1|s2|s3 from front matter or first Subject heading."""
    s = _subject_from_meta(meta)
    if s:
        return s
    m = SUBJECT_SECTION_RE.search(body)
    if m:
        return m.group(1).lower()
    return None


def parse_problems_markdown(
    text: str,
    *,
    inferred_subject: str | None = None,
) -> ProblemsDocument:
    """
    Parse problems structured markdown into a ProblemsDocument.

    Args:
        text: Model output (markdown + fenced YAML).
        inferred_subject: When the model omits subject in front matter / headings, use this
            key (typically ``detect_subject`` on the source Nougat markdown).

    Raises:
        ValueError: On missing subject, no YAML blocks, or invalid records.
    """
    if not (text or "").strip():
        raise ValueError("Problems markdown is empty")

    meta, body = _parse_front_matter(text)
    fmt = meta.get("format")
    if fmt is not None and fmt != FORMAT_PROBLEMS:
        logger.info("Problems markdown format is %r (expected %s)", fmt, FORMAT_PROBLEMS)

    subject = _subject_from_front_or_body(meta, body)
    if subject is None and isinstance(inferred_subject, str) and inferred_subject.lower() in (
        "s1",
        "s2",
        "s3",
    ):
        subject = inferred_subject.lower()
        logger.warning(
            "Problems markdown: no subject in model output; using %s from source document headers",
            subject,
        )
    sections = _split_subject_sections(body)

    if sections:
        if subject and sections[0][0] != subject:
            logger.warning(
                "Front matter subject %s differs from first section %s; using sections",
                subject,
                sections[0][0],
            )
        problems_by_subj: dict[str, list[ProblemRecord]] = {"s1": [], "s2": [], "s3": []}
        for subj, sec_body in sections:
            if subj not in problems_by_subj:
                raise ValueError(f"Invalid subject section: {subj}")
            for idx, block in enumerate(_iter_yaml_fence_bodies(sec_body, allow_plain_fence=True)):
                data = _safe_load_yaml_block(block, context=f"problems {subj} block {idx + 1}")
                problems_by_subj[subj].append(ProblemRecord.model_validate(data))
        # Accept any subset of non-empty subjects.
        non_empty = [k for k in ("s1", "s2", "s3") if problems_by_subj[k]]
        if non_empty:
            kwargs = {k: problems_by_subj[k] for k in non_empty}
            return ProblemsDocument.model_validate(kwargs)
        if len(non_empty) == 0:
            # Models often emit ## Subject before the YAML but use ``` without "yaml" or put
            # fences outside the section slice; scan the full body once.
            blocks_fb = _iter_yaml_fence_bodies(body, allow_plain_fence=True)
            if blocks_fb:
                subj_fb = sections[0][0]
                logger.warning(
                    "No YAML under ## Subject sections (%d section(s)); "
                    "using %d fenced block(s) from full document for subject %s",
                    len(sections),
                    len(blocks_fb),
                    subj_fb,
                )
                problems_fb: list[ProblemRecord] = []
                for idx, block in enumerate(blocks_fb):
                    data = _safe_load_yaml_block(
                        block, context=f"problems {subj_fb} block {idx + 1} (full-body fallback)"
                    )
                    problems_fb.append(ProblemRecord.model_validate(data))
                return ProblemsDocument.model_validate({subj_fb: problems_fb})
            # Last fallback: parse unfenced YAML bodies directly under ## Problem headings.
            problems_unfenced: dict[str, list[ProblemRecord]] = {"s1": [], "s2": [], "s3": []}
            for subj, sec_body in sections:
                unfenced_blocks = _iter_unfenced_problem_yaml_bodies(sec_body)
                if unfenced_blocks:
                    logger.warning(
                        "Problems markdown: using %d unfenced YAML problem block(s) for %s",
                        len(unfenced_blocks),
                        subj,
                    )
                for idx, block in enumerate(unfenced_blocks):
                    data = _safe_load_yaml_block(
                        block,
                        context=f"problems {subj} block {idx + 1} (unfenced fallback)",
                    )
                    problems_unfenced[subj].append(ProblemRecord.model_validate(data))
            non_empty_unfenced = [k for k in ("s1", "s2", "s3") if problems_unfenced[k]]
            if non_empty_unfenced:
                kwargs = {k: problems_unfenced[k] for k in non_empty_unfenced}
                return ProblemsDocument.model_validate(kwargs)
            # Final fallback for heading-based markdown output (no YAML at all).
            heading_based: dict[str, list[ProblemRecord]] = {"s1": [], "s2": [], "s3": []}
            for subj, sec_body in sections:
                heading_records = _parse_problems_from_problem_heading_sections(sec_body)
                if heading_records:
                    logger.warning(
                        "Problems markdown: using %d heading-based problem block(s) for %s",
                        len(heading_records),
                        subj,
                    )
                for row in heading_records:
                    heading_based[subj].append(ProblemRecord.model_validate(row))
            non_empty_heading = [k for k in ("s1", "s2", "s3") if heading_based[k]]
            if non_empty_heading:
                kwargs = {k: heading_based[k] for k in non_empty_heading}
                return ProblemsDocument.model_validate(kwargs)
        raise ValueError("Problems markdown has Subject sections but no problem blocks were parsed")

    if not subject:
        raise ValueError(
            "Problems markdown: missing subject (front matter, ## Subject sN / ## Subiect sN, "
            "or inferred_subject from source document)"
        )

    blocks = _iter_yaml_fence_bodies(body, allow_plain_fence=True)
    if not blocks:
        raise ValueError("Problems markdown: no ```yaml fences found")
    problems = []
    for idx, block in enumerate(blocks):
        data = _safe_load_yaml_block(block, context=f"problems block {idx + 1}")
        problems.append(ProblemRecord.model_validate(data))
    return ProblemsDocument.model_validate({subject: problems})


def parse_solutions_markdown(
    text: str,
    *,
    inferred_subject: str | None = None,
) -> SolutionsDocument:
    """
    Parse solutions structured markdown into a SolutionsDocument.

    Args:
        text: Model output (markdown + fenced YAML).
        inferred_subject: When the model omits ``## Subject sN``, assign all solution
            blocks to this key (typically from ``detect_subject`` on the source markdown).

    Raises:
        ValueError: On missing sections, no YAML blocks, or invalid records.
    """
    if not (text or "").strip():
        raise ValueError("Solutions markdown is empty")

    meta, body = _parse_front_matter(text)
    fmt = meta.get("format")
    if fmt is not None and fmt != FORMAT_SOLUTIONS:
        logger.info("Solutions markdown format is %r (expected %s)", fmt, FORMAT_SOLUTIONS)

    sections = _split_subject_sections(body)
    if not sections:
        subj_hint = inferred_subject or _subject_from_meta(meta)
        if isinstance(subj_hint, str) and subj_hint.lower() in ("s1", "s2", "s3"):
            subj_key = subj_hint.lower()
            blocks = _iter_yaml_fence_bodies(
                body,
                allow_plain_fence=True,
                plain_fence_predicate=_try_parse_solution_plain_fence,
            )
            if not blocks:
                raise ValueError(
                    "Solutions markdown: no Subject headings and no solution YAML fences in body "
                    f"(expected subject {subj_key} from source or front matter)"
                )
            logger.warning(
                "Solutions markdown: no Subject/Subiect headings; assigning %d fenced block(s) to %s",
                len(blocks),
                subj_key,
            )
            recs_s1: list[SolutionS1Record] = []
            recs_s23: list[SolutionS23Record] = []
            for idx, block in enumerate(blocks):
                data = _safe_load_yaml_block(
                    block, context=f"solutions {subj_key} block {idx + 1} (no-heading fallback)"
                )
                if subj_key == "s1":
                    recs_s1.append(SolutionS1Record.model_validate(data))
                else:
                    recs_s23.append(SolutionS23Record.model_validate(data))
            return SolutionsDocument.model_validate({subj_key: recs_s1 or recs_s23})
        # Last resort: model returned fenced solution YAML but no subject signal anywhere.
        blocks_lr = _iter_yaml_fence_bodies(
            body,
            allow_plain_fence=True,
            plain_fence_predicate=_try_parse_solution_plain_fence,
        )
        if blocks_lr:
            logger.warning(
                "Solutions markdown: no subject hint (headings, front matter, or source stem); "
                "assigning %d fenced block(s) to s1 — rename file with _s1/_s2/_s3 suffix if wrong",
                len(blocks_lr),
            )
            recs_lr: list[SolutionS1Record] = []
            for idx, block in enumerate(blocks_lr):
                data = _safe_load_yaml_block(
                    block, context=f"solutions s1 block {idx + 1} (last-resort fallback)"
                )
                recs_lr.append(SolutionS1Record.model_validate(data))
            return SolutionsDocument.model_validate({"s1": recs_lr})
        raise ValueError(
            "Solutions markdown: no ## Subject sN (or ###) sections found; "
            "add headings, or set `subject: s1` (s2/s3) in YAML front matter, "
            "or use a source filename ending with _s1/_s2/_s3, "
            "or ensure the source markdown contains Subiectul I/II/III (or Subiect I/II/III)"
        )

    kwargs: dict[str, Any] = {}
    for subj, sec_body in sections:
        if subj not in ("s1", "s2", "s3"):
            raise ValueError(f"Invalid subject section: {subj}")
        records_s1: list[SolutionS1Record] = []
        records_s23: list[SolutionS23Record] = []
        for idx, block in enumerate(
            _iter_yaml_fence_bodies(
                sec_body,
                allow_plain_fence=True,
                plain_fence_predicate=_try_parse_solution_plain_fence,
            )
        ):
            data = _safe_load_yaml_block(block, context=f"solutions {subj} block {idx + 1}")
            if subj == "s1":
                records_s1.append(SolutionS1Record.model_validate(data))
            else:
                records_s23.append(SolutionS23Record.model_validate(data))
        if subj == "s1" and records_s1:
            kwargs[subj] = records_s1
        if subj in ("s2", "s3") and records_s23:
            kwargs[subj] = records_s23

    if not kwargs and sections:
        blocks_fb = _iter_yaml_fence_bodies(
            body,
            allow_plain_fence=True,
            plain_fence_predicate=_try_parse_solution_plain_fence,
        )
        if blocks_fb:
            subj_fb = sections[0][0]
            logger.warning(
                "No YAML under ## Subject sections for solutions; "
                "using %d fenced block(s) from full document for subject %s",
                len(blocks_fb),
                subj_fb,
            )
            recs_s1: list[SolutionS1Record] = []
            recs_s23: list[SolutionS23Record] = []
            for idx, block in enumerate(blocks_fb):
                data = _safe_load_yaml_block(
                    block, context=f"solutions {subj_fb} block {idx + 1} (full-body fallback)"
                )
                if subj_fb == "s1":
                    recs_s1.append(SolutionS1Record.model_validate(data))
                else:
                    recs_s23.append(SolutionS23Record.model_validate(data))
            kwargs[subj_fb] = recs_s1 or recs_s23

    if not kwargs:
        raise ValueError("Solutions markdown: no solution records parsed")
    return SolutionsDocument.model_validate(kwargs)


def parse_merged_markdown(text: str) -> MergedDocument:
    """
    Parse merged structured markdown into a MergedDocument.

    Raises:
        ValueError: On invalid structure or YAML.
    """
    if not (text or "").strip():
        raise ValueError("Merged markdown is empty")

    meta, body = _parse_front_matter(text)
    fmt = meta.get("format")
    if fmt is not None and fmt != FORMAT_MERGED:
        logger.info("Merged markdown format is %r (expected %s)", fmt, FORMAT_MERGED)

    sections = _split_subject_sections(body)
    if not sections:
        raise ValueError("Merged markdown: no ## Subject sN sections found")

    kwargs: dict[str, Any] = {}
    for subj, sec_body in sections:
        blocks = _iter_yaml_fence_bodies(
            sec_body,
            allow_plain_fence=True,
            plain_fence_predicate=_try_parse_merged_plain_fence,
        )
        if not blocks:
            continue
        if subj == "s1":
            rows = []
            for idx, block in enumerate(blocks):
                data = _safe_load_yaml_block(block, context=f"merged s1 block {idx + 1}")
                rows.append(MergedS1Record.model_validate(data))
            kwargs["s1"] = rows
        else:
            rows = []
            for idx, block in enumerate(blocks):
                data = _safe_load_yaml_block(block, context=f"merged {subj} block {idx + 1}")
                rows.append(MergedS23Record.model_validate(data))
            kwargs[subj] = rows

    doc = MergedDocument.model_validate(kwargs)
    if not doc.to_merge_dict():
        raise ValueError("Merged markdown: no problems parsed under any subject")
    return doc


def _dump_yaml_mapping(data: dict[str, Any]) -> str:
    """Serialize mapping to YAML string for embedding in a fence."""
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    ).rstrip()


def serialize_problems_document(doc: ProblemsDocument) -> str:
    """Write problems document to canonical markdown."""
    keys = [k for k in ("s1", "s2", "s3") if getattr(doc, k)]
    lines = [
        "# Exam parser — structured problems v1",
        "",
        "---",
        f"format: {FORMAT_PROBLEMS}",
        "---",
        "",
    ]
    if len(keys) == 1:
        lines.insert(4, f"subject: {keys[0]}")
    for key in keys:
        problems = getattr(doc, key) or []
        lines.append(f"## Subject {key}")
        lines.append("")
        for _i, p in enumerate(problems):
            lines.append("## Problem")
            lines.append("")
            lines.append("```yaml")
            d = p.model_dump(mode="python")
            lines.append(_dump_yaml_mapping(d))
            lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def serialize_solutions_document(doc: SolutionsDocument) -> str:
    """Write solutions document to canonical markdown."""
    lines = [
        "# Exam parser — structured solutions v1",
        "",
        "---",
        f"format: {FORMAT_SOLUTIONS}",
        "---",
        "",
    ]
    for key in ("s1", "s2", "s3"):
        lst = getattr(doc, key, None)
        if not lst:
            continue
        lines.append(f"## Subject {key}")
        lines.append("")
        for _r in lst:
            lines.append("## Solution")
            lines.append("")
            lines.append("```yaml")
            lines.append(_dump_yaml_mapping(_r.model_dump(mode="python")))
            lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _solution_steps_to_plain(obj: Any) -> Any:
    """Recursively convert SolutionStep models to dicts for YAML dump."""
    if isinstance(obj, SolutionStep):
        return {"step": obj.step, "score": obj.score}
    if isinstance(obj, list):
        return [_solution_steps_to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _solution_steps_to_plain(v) for k, v in obj.items()}
    return obj


def serialize_merged_document(doc: MergedDocument) -> str:
    """Write merged document to canonical markdown."""
    lines = [
        "# Exam parser — structured merged v1",
        "",
        "---",
        f"format: {FORMAT_MERGED}",
        "---",
        "",
    ]
    for key in ("s1", "s2", "s3"):
        lst = getattr(doc, key, None)
        if not lst:
            continue
        lines.append(f"## Subject {key}")
        lines.append("")
        for row in lst:
            lines.append("## Problem")
            lines.append("")
            lines.append("```yaml")
            raw = _solution_steps_to_plain(row.model_dump(mode="python"))
            lines.append(_dump_yaml_mapping(raw))
            lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def merged_document_to_rows_dict(doc: MergedDocument) -> dict[str, Any]:
    """Alias for load_to_db: same mapping as legacy merged JSON."""
    return doc.to_merge_dict()


def serialize_problems_from_normalized_dict(data: dict[str, Any]) -> str:
    """
    Build canonical problems markdown from a normalized exam dict (single s-key).

    Raises:
        ValueError: If the dict does not match the expected problem schema.
    """
    if not data:
        raise ValueError("Empty problems dict")
    kwargs: dict[str, list[ProblemRecord]] = {}
    for key in ("s1", "s2", "s3"):
        lst = data.get(key)
        if isinstance(lst, list) and len(lst) > 0:
            kwargs[key] = [ProblemRecord.model_validate(x) for x in lst if isinstance(x, dict)]
    if not kwargs:
        raise ValueError("No problem lists to serialize")
    doc = ProblemsDocument.model_validate(kwargs)
    return serialize_problems_document(doc)


def serialize_solutions_from_normalized_dict(data: dict[str, Any]) -> str:
    """
    Build canonical solutions markdown from normalized solution dict (s1/s2/s3 lists).

    Raises:
        ValueError: If no non-empty subject lists are present.
    """
    kwargs: dict[str, Any] = {}
    if isinstance(data.get("s1"), list) and len(data["s1"]) > 0:
        kwargs["s1"] = [SolutionS1Record.model_validate(x) for x in data["s1"] if isinstance(x, dict)]
    for key in ("s2", "s3"):
        if isinstance(data.get(key), list) and len(data[key]) > 0:
            kwargs[key] = [SolutionS23Record.model_validate(x) for x in data[key] if isinstance(x, dict)]
    if not kwargs:
        raise ValueError("No solution lists to serialize")
    doc = SolutionsDocument.model_validate(kwargs)
    return serialize_solutions_document(doc)
