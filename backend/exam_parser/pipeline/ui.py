"""Streamlit dashboard for the exam parsing pipeline.

Run from repo root:
    uv run poe exam_parser_ui
  or (alias):
    uv run poe pipeline_ui
  or directly:
    uv run streamlit run backend/exam_parser/pipeline/ui.py
"""
from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import streamlit as st

from exam_parser.pipeline.model_options import DEFAULT_OLLAMA_MODEL_ID

# ── Constants ─────────────────────────────────────────────────────────────────

STEP_NAMES: list[str] = [
    "extract_problems",
    "parse_problems",
    "extract_solutions",
    "parse_solutions",
    "merge",
    "load_to_db",
    "index_to_vector_db",
]

STEP_LABELS: dict[str, str] = {
    "extract_problems":   "Extract\nProblems",
    "parse_problems":     "Parse\nProblems",
    "extract_solutions":  "Extract\nSolutions",
    "parse_solutions":    "Parse\nSolutions",
    "merge":              "Merge",
    "load_to_db":         "Load\nto DB",
    "index_to_vector_db": "Index\nVectors",
}

STEP_ICONS: dict[str, str] = {
    "extract_problems":   "📥",
    "parse_problems":     "📄",
    "extract_solutions":  "📥",
    "parse_solutions":    "📝",
    "merge":              "🔗",
    "load_to_db":         "🗄",
    "index_to_vector_db": "🔍",
}

_PIPELINE_DIR  = Path(__file__).resolve().parent          # pipeline/
_EXAM_PARSER   = _PIPELINE_DIR.parent                     # exam_parser/
RUNS_DIR       = _EXAM_PARSER / "runs"
REPO_ROOT      = _EXAM_PARSER.parent.parent               # profu/
RUN_INPUTS_FILENAME = "ui_last_inputs.json"

ANSI_RE        = re.compile(r"\x1b\[[0-9;]*m")
STEP_RUN_RE    = re.compile(r"Running (?:step|parallel steps)[:\s]+(.+?)(?:\s*===|$)")
BRACKET_RE     = re.compile(r"^\[(\w+)\]")
MAX_LOG_LINES  = 500

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Exam Pipeline",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state ─────────────────────────────────────────────────────────────

def _init() -> None:
    defs: dict = {
        "proc":            None,
        "_q":              None,
        "all_logs":        [],
        "step_logs":       {s: [] for s in STEP_NAMES},
        "running_steps":   set(),
        "current_step":    None,
        "selected_step":   None,
        "selected_step_pinned": False,
        "pipeline_status": "idle",      # idle | running | failed | done
        "failed_step":     None,
        "last_error":      None,
        "_nougat_device":  "cuda",
        "_run_name_seen":  "",
        "_run_inputs_cache": {},
        "step_progress":   {s: {"status": "pending", "completed": 0, "total": 0, "fraction": 0.0}
                            for s in STEP_NAMES},
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state._q is None:
        st.session_state._q = queue.Queue()

_init()


def _run_inputs_path(run_name: str) -> Path:
    """Return path of persisted UI input snapshot for a given run."""
    return RUNS_DIR / run_name / RUN_INPUTS_FILENAME


def _load_saved_run_inputs(run_name: str) -> dict | None:
    """Load saved UI paths for a run, from memory cache or run-local JSON file."""
    if not run_name:
        return None

    cache = st.session_state.get("_run_inputs_cache", {})
    if isinstance(cache, dict) and run_name in cache:
        cached = cache.get(run_name)
        if isinstance(cached, dict):
            return cached

    path = _run_inputs_path(run_name)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        if not isinstance(st.session_state.get("_run_inputs_cache"), dict):
            st.session_state._run_inputs_cache = {}
        st.session_state._run_inputs_cache[run_name] = payload
        return payload
    except Exception as exc:
        print(
            f"[exam_parser UI] Failed to load saved run inputs for {run_name}: {exc}",
            file=sys.stderr,
        )
        return None


def _save_run_inputs(run_name: str, problems_dir: str, solutions_dir: str, source: str) -> None:
    """Persist UI input values for auto-fill when the same run name is used later."""
    if not run_name:
        return
    payload = {
        "problems_dir": problems_dir,
        "solutions_dir": solutions_dir,
        "source": source,
    }
    try:
        path = _run_inputs_path(run_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if not isinstance(st.session_state.get("_run_inputs_cache"), dict):
            st.session_state._run_inputs_cache = {}
        st.session_state._run_inputs_cache[run_name] = payload
    except Exception as exc:
        print(
            f"[exam_parser UI] Failed to save run inputs for {run_name}: {exc}",
            file=sys.stderr,
        )


def _maybe_autofill_paths_from_run_name() -> None:
    """When run name changes, auto-fill problems/solutions paths from saved run inputs."""
    run_name = str(st.session_state.get("_run_name", "")).strip()
    seen = str(st.session_state.get("_run_name_seen", ""))
    if run_name == seen:
        return
    st.session_state._run_name_seen = run_name
    if not run_name:
        return

    saved = _load_saved_run_inputs(run_name)
    if not isinstance(saved, dict):
        return

    prob = saved.get("problems_dir")
    sol = saved.get("solutions_dir")
    src = saved.get("source")
    if isinstance(prob, str) and prob.strip():
        st.session_state._prob_dir = prob
    if isinstance(sol, str) and sol.strip():
        st.session_state._sol_dir = sol
    if isinstance(src, str) and src in ("var", "exam", "test"):
        st.session_state._source = src

# ── Log helpers ───────────────────────────────────────────────────────────────

def _strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def _parse_line(raw: str) -> dict:
    """Parse one stdout line into a normalized log entry used by the UI."""
    s = _strip_ansi(raw).strip()
    if s.startswith("{"):
        try:
            d = json.loads(s)
            return {
                "level":   str(d.get("level", "INFO")).upper(),
                "message": d.get("message", s),
            }
        except json.JSONDecodeError:
            pass
    # Heuristic fallback so Python tracebacks and non-JSON fatal lines
    # are still surfaced as errors in the UI banner.
    if (
        "traceback" in s.lower()
        or s.startswith("Error:")
        or s.startswith("Exception:")
        or "CRITICAL" in s
    ):
        return {"level": "ERROR", "message": s}
    return {"level": "INFO", "message": s}


def _build_error_excerpt_from_recent_logs(max_lines: int = 30) -> str | None:
    """Build a concise multiline error excerpt from recent pipeline logs."""
    recent_logs = st.session_state.all_logs[-80:]
    if not recent_logs:
        return None

    # Try to capture the most recent traceback block and the exception tail.
    traceback_start_index = None
    for idx in range(len(recent_logs) - 1, -1, -1):
        msg = str(recent_logs[idx].get("message", "")).strip()
        if "traceback (most recent call last):" in msg.lower():
            traceback_start_index = idx
            break

    if traceback_start_index is not None:
        traceback_lines: list[str] = []
        for log_entry in recent_logs[traceback_start_index:]:
            msg = str(log_entry.get("message", "")).rstrip()
            if msg:
                traceback_lines.append(msg)
            if len(traceback_lines) >= max_lines:
                break
        if traceback_lines:
            return "\n".join(traceback_lines)

    # Fallback: return the latest non-empty lines.
    fallback_lines: list[str] = []
    for log_entry in reversed(recent_logs):
        msg = str(log_entry.get("message", "")).strip()
        if msg:
            fallback_lines.append(msg)
        if len(fallback_lines) >= max_lines:
            break
    if not fallback_lines:
        return None
    fallback_lines.reverse()
    return "\n".join(fallback_lines)


def _is_unhelpful_error_message(msg: str | None) -> bool:
    """Return True for placeholder-like errors that should be replaced with richer excerpts."""
    if not msg:
        return True
    m = msg.strip().lower()
    return (
        m.startswith("traceback (most recent call last):")
        or "without a structured error log" in m
        or m.startswith("pipeline process exited with code")
    )


def _detect_steps(msg: str) -> list[str]:
    """Return list of step names mentioned as currently running in this message."""
    m = STEP_RUN_RE.search(msg)
    if m:
        return [s for s in STEP_NAMES if s in m.group(1)]
    m2 = BRACKET_RE.match(msg)
    if m2 and m2.group(1) in STEP_NAMES:
        return [m2.group(1)]
    return []


def _infer_step_from_log_message(msg: str) -> str | None:
    """Resolve pipeline step from log text (e.g. ``[merge]`` prefix used by step loggers)."""
    for sn in STEP_NAMES:
        if f"[{sn}]" in msg:
            return sn
    return None


def _preferred_failed_step_for_error(msg: str) -> str | None:
    """Pick which timeline node to mark failed when an ERROR line is seen."""
    inferred = _infer_step_from_log_message(msg)
    if inferred is not None:
        return inferred
    cur = st.session_state.current_step
    if isinstance(cur, str) and cur in STEP_NAMES:
        return cur
    for sn in STEP_NAMES:
        if sn in st.session_state.running_steps:
            return sn
    return None


def _stop_pipeline_on_logged_error(msg: str) -> None:
    """
    Fail the run, highlight the step in the timeline, and terminate the CLI subprocess.
    Called when a log line is parsed as ERROR while a run is active.
    """
    if st.session_state.pipeline_status != "running":
        return
    failed = _preferred_failed_step_for_error(msg)
    st.session_state.pipeline_status = "failed"
    if failed is not None:
        st.session_state.failed_step = failed
    st.session_state.running_steps = set()
    proc = st.session_state.proc
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
        except Exception as exc:
            print(f"[exam_parser UI] Failed to terminate pipeline subprocess: {exc}", file=sys.stderr)


def _reader(proc: subprocess.Popen, q: queue.Queue) -> None:
    for raw in proc.stdout:           # type: ignore[union-attr]
        q.put(("line", raw.rstrip("\n")))
    q.put(("done", proc.wait()))


def _drain() -> None:
    """Consume process output queue and update timeline, logs, and failure state."""
    q: queue.Queue = st.session_state._q
    while True:
        try:
            kind, data = q.get_nowait()
        except queue.Empty:
            break

        if kind == "done":
            st.session_state.proc = None
            if data != 0:
                st.session_state.pipeline_status = "failed"
                # On failure, always try to enrich the banner with recent traceback lines.
                # This also replaces placeholder errors like bare "Traceback..." headers.
                fallback_error = _build_error_excerpt_from_recent_logs()
                if fallback_error and _is_unhelpful_error_message(st.session_state.last_error):
                    st.session_state.last_error = fallback_error
                if st.session_state.last_error is None:
                    st.session_state.last_error = (
                        f"Pipeline process exited with code {data} without a structured error log."
                    )
                print(
                    f"[exam_parser UI] Non-zero exit ({data}) with error excerpt: {st.session_state.last_error}",
                    file=sys.stderr,
                )
                if st.session_state.failed_step is None:
                    cur = st.session_state.current_step
                    if isinstance(cur, str) and cur in STEP_NAMES:
                        st.session_state.failed_step = cur
                    else:
                        for sn in STEP_NAMES:
                            if sn in st.session_state.running_steps:
                                st.session_state.failed_step = sn
                                break
                # Stop showing yellow "running" once the process has exited with failure
                st.session_state.running_steps = set()
            else:
                st.session_state.pipeline_status = "done"
                st.session_state.current_step = None
                st.session_state.running_steps = set()
            continue

        parsed = _parse_line(data)
        msg, level = parsed["message"], parsed["level"]

        # Detect step transitions
        detected = _detect_steps(msg)
        if detected:
            st.session_state.running_steps = set(detected)
            st.session_state.current_step = detected[0]
            # Auto-follow only when user did not pin a timeline step.
            if (
                st.session_state.pipeline_status == "running"
                and not st.session_state.selected_step_pinned
            ):
                st.session_state.selected_step = detected[0]

        # "Finished parallel steps" → clear running
        if "Finished parallel steps" in msg:
            st.session_state.running_steps = set()
        if "Finished step:" in msg:
            for s in STEP_NAMES:
                if s in msg:
                    st.session_state.running_steps.discard(s)

        cur = st.session_state.current_step
        entry = {"step": cur, "level": level, "message": msg}
        st.session_state.all_logs.append(entry)
        if cur and cur in st.session_state.step_logs:
            logs = st.session_state.step_logs[cur]
            logs.append(entry)
            if len(logs) > MAX_LOG_LINES:
                del logs[0]
        if level == "ERROR":
            is_traceback_header = "traceback (most recent call last):" in msg.lower()
            if is_traceback_header:
                # Do not terminate immediately on traceback header, otherwise
                # we kill the process before exception lines are emitted.
                st.session_state.last_error = _build_error_excerpt_from_recent_logs() or msg
                print(
                    "[exam_parser UI] Traceback header detected; waiting for full traceback before process termination.",
                    file=sys.stderr,
                )
            else:
                st.session_state.last_error = msg
                _stop_pipeline_on_logged_error(msg)

# ── Checkpoint / progress ─────────────────────────────────────────────────────

def _n(path: str | Path, pattern: str) -> int:
    p = Path(path)
    return len(list(p.glob(pattern))) if p.is_dir() else 0


def _refresh_progress(run_name: str, prob_dir: str, sol_dir: str) -> None:
    if not run_name:
        return

    cp_path = RUNS_DIR / run_name / "checkpoint.json"
    cp: dict = {}
    if cp_path.is_file():
        try:
            cp = json.loads(cp_path.read_text("utf-8")).get("steps", {})
        except Exception:
            pass

    root = RUNS_DIR / run_name
    n_prob   = _n(prob_dir,             "*.pdf")
    n_sol    = _n(sol_dir,              "*.pdf")
    n_merged = _n(root / "03_merged",   "*_merged.md")

    totals = {
        "extract_problems":   n_prob,
        "parse_problems":     n_prob,
        "extract_solutions":  n_sol,
        "parse_solutions":    n_sol,
        "merge":              n_prob or n_merged,
        "load_to_db":         n_merged or n_prob,
        "index_to_vector_db": 0,
    }

    running = st.session_state.running_steps
    failed  = st.session_state.failed_step
    prog: dict = {}

    for step in STEP_NAMES:
        info      = cp.get(step, {})
        cp_status = info.get("status", "pending")
        completed = len(info.get("completed_files", []))
        total     = totals[step]

        # Failed must win over running, or the node stays yellow after exit until rerun
        if step == failed and st.session_state.pipeline_status == "failed":
            status = "failed"
        elif step in running:
            status = "running"
        elif cp_status == "done":
            status = "done"
        else:
            status = "pending"

        if step == "index_to_vector_db":
            fraction = 1.0 if status == "done" else 0.0
        else:
            fraction = (completed / total) if total > 0 else (1.0 if status == "done" else 0.0)

        prog[step] = {"status": status, "completed": completed, "total": total, "fraction": fraction}

    st.session_state.step_progress = prog

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] {
    background:#0d0e14 !important; font-family:'Inter',sans-serif !important;
}
#MainMenu,footer,.stDeployButton{visibility:hidden}

/* ── Timeline ───────────────────────────────────────── */
.tl-wrap{display:flex;align-items:center;padding:24px 8px 4px;width:100%}
.tl-stack{display:flex;flex-direction:column;align-items:center;flex:0 0 auto;min-width:84px}
.tl-node{display:flex;flex-direction:column;align-items:center;gap:6px;flex:0 0 auto;min-width:84px}
.tl-circle{
    width:48px;height:48px;border-radius:50%;display:flex;align-items:center;
    justify-content:center;font-size:16px;font-weight:700;border:2.5px solid;
    transition:all .3s cubic-bezier(.4,0,.2,1);position:relative;cursor:pointer;
}
.tl-pending {background:#13141c;border-color:#2e3045;color:#4b5563}
.tl-running {background:#1a1500;border-color:#d97706;color:#fbbf24;
    box-shadow:0 0 22px rgba(251,191,36,.4);animation:tl-pulse 1.8s ease-in-out infinite}
.tl-done    {background:#0a160c;border-color:#16a34a;color:#4ade80;box-shadow:0 0 12px rgba(74,222,128,.25)}
.tl-failed  {background:#1a0808;border-color:#dc2626;color:#f87171;box-shadow:0 0 18px rgba(248,113,113,.4)}
.tl-selected::after{content:'';position:absolute;inset:-6px;border-radius:50%;
    border:2px solid rgba(255,255,255,.25)}
.tl-lbl{font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
    text-align:center;line-height:1.4;white-space:pre-line}
.tl-lbl-pending{color:#4b5563}.tl-lbl-running{color:#fbbf24}
.tl-lbl-done{color:#4ade80}   .tl-lbl-failed{color:#f87171}
.tl-step-link{
    text-decoration:none;color:inherit;cursor:pointer;
    display:flex;flex-direction:column;align-items:center;gap:6px;
}
.tl-step-link:hover .tl-circle{filter:brightness(1.12)}
.tl-conn{flex:1;height:3px;border-radius:2px;min-width:16px;margin-bottom:30px}
.tl-conn-pending{background:#1e2030}
.tl-conn-done   {background:#15803d}
.tl-conn-running{background:linear-gradient(90deg,#15803d,#d97706)}
.tl-conn-v{width:3px;min-height:22px;border-radius:2px;margin:2px 0 6px;flex-shrink:0}
.tl-conn-v-pending{background:#1e2030}
.tl-conn-v-done   {background:#15803d}
.tl-conn-v-running{background:linear-gradient(180deg,#15803d,#d97706)}

@keyframes tl-pulse{
    0%,100%{box-shadow:0 0 10px rgba(251,191,36,.25)}
    50%    {box-shadow:0 0 28px rgba(251,191,36,.6)}
}

/* ── Log window ─────────────────────────────────────── */
.log-win{
    background:#07080f;border:1px solid #1a1c2a;border-radius:10px;
    padding:14px 16px;height:420px;overflow-y:auto;
    font-family:'JetBrains Mono','Fira Code',monospace;font-size:12px;line-height:1.75;
}
.log-win::-webkit-scrollbar{width:5px}
.log-win::-webkit-scrollbar-track{background:#0d0e14}
.log-win::-webkit-scrollbar-thumb{background:#2a2c3e;border-radius:3px}
.ll-INFO   {color:#6b7280}
.ll-DEBUG  {color:#374151}
.ll-WARNING{color:#f59e0b}
.ll-ERROR  {color:#f87171;font-weight:600}

/* ── Status badge ───────────────────────────────────── */
.sb{display:inline-flex;align-items:center;gap:5px;padding:3px 12px;
    border-radius:999px;font-size:12px;font-weight:600;letter-spacing:.03em}
.sb-idle   {background:#16171f;color:#52525b;border:1px solid #27293a}
.sb-running{background:#1a1200;color:#fbbf24;border:1px solid rgba(251,191,36,.35)}
.sb-done   {background:#0a160c;color:#4ade80;border:1px solid rgba(74,222,128,.35)}
.sb-failed {background:#1a0808;color:#f87171;border:1px solid rgba(248,113,113,.35)}

/* ── Error banner ───────────────────────────────────── */
.err-banner{
    background:linear-gradient(135deg,#1a0808,#200b0b);border:1px solid #7f1d1d;
    border-radius:10px;padding:16px 20px;margin-bottom:14px;color:#fca5a5;font-size:13px;
}
.err-banner strong{color:#f87171;font-size:15px;display:block;margin-bottom:4px}

/* ── Section divider ────────────────────────────────── */
.sep{border:none;border-top:1px solid #1a1c26;margin:18px 0}

/* ── Subtle nav buttons ─────────────────────────────── */
.stButton>button{
    background:transparent!important;border:none!important;
    color:#374151!important;font-size:10px!important;padding:2px!important;
    min-height:0!important;width:100%
}
.stButton>button:hover{color:#9ca3af!important;background:rgba(255,255,255,.04)!important}
</style>
"""

# ── Timeline HTML ─────────────────────────────────────────────────────────────

def _tl_h_conn_class(prev_status: str, next_status: str) -> str:
    """CSS class for horizontal segment between two steps."""
    if prev_status == "done" and next_status in ("done", "running", "failed"):
        return "tl-conn-done" if next_status == "done" else "tl-conn-running"
    return "tl-conn-pending"


def _tl_v_conn_class(upper_status: str, lower_status: str) -> str:
    """CSS class for vertical segment between stacked parse steps."""
    if upper_status == "done" and lower_status in ("done", "running", "failed"):
        return "tl-conn-v-done" if lower_status == "done" else "tl-conn-v-running"
    return "tl-conn-v-pending"


def _tl_node_html(step: str, progress: dict, selected: str | None) -> str:
    """One timeline node (circle + label); whole node links to ?tl_step= for log selection."""
    status = progress.get(step, {}).get("status", "pending")
    icon = {"pending": STEP_ICONS[step], "running": "⚙", "done": "✓", "failed": "✗"}.get(status, "●")
    sel = " tl-selected" if step == selected else ""
    lbl = STEP_LABELS[step]
    return (
        f'<div class="tl-node">'
        f'  <a class="tl-step-link" href="?tl_step={step}" title="View logs for this step">'
        f'    <div class="tl-circle tl-{status}{sel}">{icon}</div>'
        f'    <div class="tl-lbl tl-lbl-{status}">{lbl}</div>'
        f"  </a>"
        f"</div>"
    )


def _consume_tl_step_query() -> None:
    """
    When the user clicks a timeline node, the browser opens ``?tl_step=<id>``.
    Apply that to session state and remove the param (triggers a Streamlit rerun).
    """
    qp = st.query_params
    if "tl_step" not in qp:
        return
    raw = qp.get("tl_step", "")
    val = raw[0] if isinstance(raw, (list, tuple)) else str(raw)
    if val in STEP_NAMES:
        st.session_state.selected_step = val
        st.session_state.selected_step_pinned = True
    try:
        del qp["tl_step"]
    except KeyError:
        pass


def _timeline_html(progress: dict, selected: str | None) -> str:
    """Timeline: first column stacks extract/parse for problems then solutions; then merge → DB → index."""
    parts: list[str] = []
    stack_steps = STEP_NAMES[:4]

    parts.append('<div class="tl-stack">')
    for i, step in enumerate(stack_steps):
        parts.append(_tl_node_html(step, progress, selected))
        if i < len(stack_steps) - 1:
            st_a = progress.get(stack_steps[i], {}).get("status", "pending")
            st_b = progress.get(stack_steps[i + 1], {}).get("status", "pending")
            vcls = _tl_v_conn_class(st_a, st_b)
            parts.append(f'<div class="tl-conn-v {vcls}"></div>')
    parts.append("</div>")

    for i in range(4, len(STEP_NAMES)):
        step = STEP_NAMES[i]
        prev = STEP_NAMES[i - 1]
        prev_st = progress.get(prev, {}).get("status", "pending")
        st = progress.get(step, {}).get("status", "pending")
        hcls = _tl_h_conn_class(prev_st, st)
        parts.append(f'<div class="tl-conn {hcls}"></div>')
        parts.append(_tl_node_html(step, progress, selected))

    return '<div class="tl-wrap">' + "".join(parts) + "</div>"


# ── Log panel ─────────────────────────────────────────────────────────────────

def _log_html(logs: list[dict]) -> str:
    pfx = {"INFO": "INFO ", "WARNING": "WARN ", "ERROR": "ERR  ", "DEBUG": "DBG  "}
    lines = [
        f'<div class="ll-{e["level"]}">'
        f'{pfx.get(e["level"], e["level"][:5].ljust(5))} '
        f'{e["message"].replace("<","&lt;").replace(">","&gt;")}'
        f'</div>'
        for e in logs[-400:]
    ] or ['<div class="ll-DEBUG">No logs yet...</div>']

    scroll = (
        "<script>setTimeout(()=>{"
        "var w=document.getElementById('lw');if(w)w.scrollTop=w.scrollHeight;},100)"
        "</script>"
    )
    return '<div class="log-win" id="lw">' + "".join(lines) + "</div>" + scroll


# ── Pipeline launcher ─────────────────────────────────────────────────────────

def _launch(
    run_name: str,
    prob: str,
    sol: str,
    source: str,
    dry: bool,
    overwrite: bool,
    start_from: str | None,
) -> None:
    """Start the pipeline CLI subprocess and stream its logs to the dashboard."""
    cmd = [
        sys.executable, "-m", "exam_parser.pipeline.cli",
        "--run-name", run_name,
        "--problems-dir", prob,
        "--solutions-dir", sol,
        "--source", source,
        "--ollama-model", DEFAULT_OLLAMA_MODEL_ID,
    ]
    if dry:
        cmd.append("--dry-run")
    if overwrite:
        cmd.append("--overwrite")
    if start_from:
        cmd.extend(["--start-from", start_from])

    # Clear logs for steps being re-run
    reset_from = STEP_NAMES.index(start_from) if start_from else 0
    for s in STEP_NAMES[reset_from:]:
        st.session_state.step_logs[s] = []
    if not start_from:
        st.session_state.all_logs = []

    st.session_state.current_step    = None
    st.session_state.running_steps   = set()
    st.session_state.failed_step     = None
    st.session_state.last_error      = None
    st.session_state.pipeline_status = "running"
    # Default to "All Steps" logs until an actual running step is detected.
    st.session_state.selected_step   = None
    st.session_state.selected_step_pinned = False
    st.session_state._q              = queue.Queue()

    try:
        _save_run_inputs(run_name, prob, sol, source)
        launch_env = os.environ.copy()
        launch_env["NOUGAT_DEVICE"] = st.session_state.get("_nougat_device", "cuda")
        print(f"[exam_parser UI] Launching pipeline command: {' '.join(cmd)}", file=sys.stderr)
        print(
            "[exam_parser UI] "
            f"NOUGAT_DEVICE={launch_env['NOUGAT_DEVICE']}, "
            f"CUDA_VISIBLE_DEVICES={launch_env.get('CUDA_VISIBLE_DEVICES', '<unset>')}, "
            f"PYTORCH_NVML_BASED_CUDA_CHECK={launch_env.get('PYTORCH_NVML_BASED_CUDA_CHECK', '<unset>')}",
            file=sys.stderr,
        )
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(REPO_ROOT),
            env=launch_env,
        )
        st.session_state.proc = proc
        threading.Thread(target=_reader, args=(proc, st.session_state._q), daemon=True).start()
    except Exception as exc:
        error_message = f"Failed to launch pipeline subprocess: {exc}"
        print(f"[exam_parser UI] {error_message}", file=sys.stderr)
        st.session_state.pipeline_status = "failed"
        st.session_state.last_error = error_message
        st.session_state.proc = None


def _folder_picker(label: str, key: str, placeholder: str) -> None:
    """
    Folder browser popover + text field. Selected path is applied via a pending key
    before ``text_input`` is created, because Streamlit forbids assigning to the same
    ``session_state`` key after the widget is instantiated.
    """
    nav_key = f"{key}_nav"
    pending_key = f"{key}_pending_path"
    if pending_key in st.session_state:
        st.session_state[key] = st.session_state.pop(pending_key)
    if key not in st.session_state:
        st.session_state[key] = ""

    c1, c2 = st.columns([6, 1])
    with c1:
        st.text_input(label, key=key, placeholder=placeholder)
    with c2:
        st.markdown('<div style="margin-top:27.5px"></div>', unsafe_allow_html=True)
        with st.popover("📁"):
            current_val = st.session_state[key]
            if nav_key not in st.session_state:
                p = Path(current_val).resolve() if current_val else Path.cwd()
                st.session_state[nav_key] = p if p.is_dir() else Path.cwd()
            
            nav_path = Path(st.session_state[nav_key]).resolve()
            st.markdown(f"**Dir:** `{nav_path}`")
            
            c_up, c_sel = st.columns([1, 1.5])
            with c_up:
                if st.button("⬆️ Up", key=f"{key}_up"):
                    st.session_state[nav_key] = nav_path.parent
                    st.rerun()
            with c_sel:
                if st.button("✅ Select", key=f"{key}_sel", type="primary", use_container_width=True):
                    st.session_state[pending_key] = str(nav_path)
                    st.rerun()

            st.divider()
            try:
                subdirs = sorted([d for d in nav_path.iterdir() if d.is_dir() and not d.name.startswith(".")])
                for d in subdirs:
                    if st.button(f"📁 {d.name}", key=f"{key}_dir_{d.name}", use_container_width=True):
                        st.session_state[nav_key] = d
                        st.rerun()
            except PermissionError:
                st.error("Permission denied")
            except FileNotFoundError:
                st.session_state[nav_key] = Path.cwd()
                st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    _consume_tl_step_query()
    _maybe_autofill_paths_from_run_name()

    # Drain queue + refresh progress before rendering
    _drain()
    run_name = st.session_state.get("_run_name", "")
    prob_dir = st.session_state.get("_prob_dir", "")
    sol_dir  = st.session_state.get("_sol_dir",  "")
    _refresh_progress(run_name, prob_dir, sol_dir)

    status   = st.session_state.pipeline_status
    progress = st.session_state.step_progress
    is_run   = st.session_state.proc is not None

    # ── Header ────────────────────────────────────────────────────────────────
    h1, h2 = st.columns([6, 1])
    with h1:
        st.markdown("## 🔬 Exam Parsing Pipeline")
    with h2:
        badge = {
            "idle":    '<span class="sb sb-idle">○ Idle</span>',
            "running": '<span class="sb sb-running">⚙ Running</span>',
            "done":    '<span class="sb sb-done">✓ Complete</span>',
            "failed":  '<span class="sb sb-failed">✗ Failed</span>',
        }
        st.markdown(badge.get(status, ""), unsafe_allow_html=True)

    # ── Error banner ──────────────────────────────────────────────────────────
    if status == "failed" and st.session_state.last_error:
        raw_error = str(st.session_state.last_error)[:1400]
        err_msg = raw_error.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        st.markdown(
            f'<div class="err-banner">'
            f'<strong>⛔ Pipeline Failed</strong>'
            f'{err_msg}<br>'
            f'<small style="opacity:.7">Fix the issue, then press <b>Resume</b> below.</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Inputs expander ───────────────────────────────────────────────────────
    with st.expander("⚙  Configuration", expanded=(status == "idle")):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Run Name", key="_run_name", placeholder="e.g. bac_2024")
        with c2:
            _folder_picker("Problems Directory", "_prob_dir", "/path/to/problems_pdfs")
        with c3:
            _folder_picker("Solutions Directory", "_sol_dir", "/path/to/solutions_pdfs")

        c4, c5, c6 = st.columns(3)
        with c4:
            st.selectbox("Source", ["var", "exam", "test"], key="_source")
        with c5:
            st.checkbox("Dry Run", key="_dry_run")
        with c6:
            st.checkbox("Overwrite", key="_overwrite")

        st.selectbox(
            "Nougat Device",
            ["auto", "cuda", "cuda:0", "mps", "cpu"],
            key="_nougat_device",
            help="Select device for Nougat extraction. Default is cuda (fail-fast if GPU is unavailable).",
        )
        st.markdown("**Ollama (markdown → JSON)**")
        st.caption(
            f"Model fix: **{DEFAULT_OLLAMA_MODEL_ID}**. Rulează `ollama pull {DEFAULT_OLLAMA_MODEL_ID}` dacă nu e instalat."
        )
        st.caption(
            "Extragere PDF: **Nougat** local (`NOUGAT_DEVICE=cuda` implicit, fail-fast dacă GPU nu e disponibil). "
            "Index vectori: `gemini-embedding-001`."
        )

    st.markdown('<hr class="sep">', unsafe_allow_html=True)

    # ── Action buttons ────────────────────────────────────────────────────────
    has_name = bool(st.session_state.get("_run_name", "").strip())
    b1, b2, b3, b4 = st.columns([2, 2, 2, 4])

    with b1:
        if st.button("▶  Run Pipeline", disabled=(is_run or not has_name),
                     type="primary", use_container_width=True):
            _launch(
                st.session_state._run_name,
                st.session_state._prob_dir,
                st.session_state._sol_dir,
                st.session_state._source,
                st.session_state._dry_run,
                st.session_state._overwrite,
                None,
            )
            st.rerun()

    with b2:
        opts  = ["(from beginning)"] + STEP_NAMES
        def_i = 0
        if st.session_state.failed_step in STEP_NAMES:
            def_i = STEP_NAMES.index(st.session_state.failed_step) + 1
        resume_choice = st.selectbox(
            "Resume step", opts, index=def_i,
            key="_resume_step", label_visibility="collapsed",
        )

    with b3:
        resume_type = "primary" if status == "failed" else "secondary"
        if st.button("↩  Resume", disabled=(is_run or not has_name),
                     type=resume_type, use_container_width=True):
            sf = None if resume_choice == "(from beginning)" else resume_choice
            _launch(
                st.session_state._run_name,
                st.session_state._prob_dir,
                st.session_state._sol_dir,
                st.session_state._source,
                st.session_state._dry_run,
                st.session_state._overwrite,
                sf,
            )
            st.rerun()

    with b4:
        if is_run and st.button("⏹  Stop", use_container_width=True):
            if st.session_state.proc:
                st.session_state.proc.terminate()
            st.session_state.pipeline_status = "failed"
            st.session_state.failed_step = st.session_state.current_step
            st.rerun()

    st.markdown('<hr class="sep">', unsafe_allow_html=True)

    # ── Timeline ─────────────────────────────────────────────────────────────
    selected = st.session_state.selected_step
    st.caption("Click a step (icon or label) to show its logs below.")
    if selected and st.session_state.selected_step_pinned:
        if st.button("Unpin step selection", key="unpin_step_selection"):
            st.session_state.selected_step_pinned = False
            st.session_state.selected_step = st.session_state.current_step
            st.rerun()
    # ``st.html`` keeps ``<a href="?tl_step=...">``; ``st.markdown`` may strip links.
    st.html(_timeline_html(progress, selected))

    # ── Progress detail for selected step ────────────────────────────────────
    if selected:
        info = progress.get(selected, {})
        frac = info.get("fraction", 0.0)
        comp = info.get("completed", 0)
        tot  = info.get("total",     0)
        stat = info.get("status",    "pending")

        pc1, pc2, pc3 = st.columns([4, 1, 1])
        with pc1:
            st.progress(frac)
        with pc2:
            status_text = "✓ Done" if stat == "done" else ("⚙ Running" if stat == "running"
                    else ("✗ Failed" if stat == "failed" else "— Pending"))
            # Streamlit requires a non-empty label (a11y); hide it to keep the compact layout.
            st.metric(
                "Stare pas",
                status_text,
                label_visibility="collapsed",
            )
        with pc3:
            count_text = f"{comp}/{tot}" if tot else ("✓" if stat == "done" else "—")
            st.metric(
                "Progres fișiere",
                count_text,
                label_visibility="collapsed",
            )

    st.markdown('<hr class="sep">', unsafe_allow_html=True)

    # ── Log panel ─────────────────────────────────────────────────────────────
    lh1, lh2 = st.columns([5, 1])
    log_label = STEP_LABELS.get(selected, "All Steps").replace("\n", " ") if selected else "All Steps"
    with lh1:
        st.markdown(f"**Logs — {log_label}**")
    with lh2:
        if st.button("Clear logs", key="clr"):
            if selected:
                st.session_state.step_logs[selected] = []
            else:
                st.session_state.all_logs = []
            st.rerun()

    logs = st.session_state.step_logs.get(selected, []) if selected else st.session_state.all_logs
    if selected and not logs and st.session_state.all_logs:
        # If step-specific logs are empty (e.g. failure before first step), show global logs.
        logs = st.session_state.all_logs
    st.markdown(_log_html(logs), unsafe_allow_html=True)

    issue_logs = [
        entry
        for entry in st.session_state.all_logs
        if entry.get("level") in ("WARNING", "ERROR")
    ]
    if issue_logs:
        st.markdown("**Recent Issues**")
        st.markdown(_log_html(issue_logs[-80:]), unsafe_allow_html=True)

    # ── Auto-refresh while pipeline is running ────────────────────────────────
    if is_run:
        time.sleep(0.5)
        st.rerun()


main()
