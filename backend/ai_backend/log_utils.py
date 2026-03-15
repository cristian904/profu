"""
Central JSON logging for ai_backend.
Every log line is a single JSON object with source, location, level, message, user_id, traceback.
Includes colored terminal formatting (level + message value highlight) when output is a TTY.
"""
import datetime
import inspect
import json
import logging
import sys
from typing import Literal, Optional
from uuid import UUID

# Dedicated logger so it can be configured separately (message-only formatter).
_LOGGER = logging.getLogger("ai_backend.json")

# ANSI color codes for terminal output (only used when stderr is a TTY)
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_CYAN = "\033[36m"

_LEVEL_COLORS = {
    "DEBUG": _CYAN,
    "INFO": _GREEN,
    "WARNING": _YELLOW,
    "ERROR": _RED,
}

# Highlight color for the JSON "message" value (visible but distinct from level)
_MESSAGE_VALUE_COLOR = _BOLD + _CYAN


def _highlight_message_value(json_str: str) -> str:
    """
    Find the "message" key's string value in the JSON and wrap it in ANSI color.
    Handles escaped quotes inside the value. Returns original string on any failure.
    """
    try:
        key = '"message"'
        idx = json_str.find(key)
        if idx == -1:
            return json_str
        # Skip past key and optional colon/space to opening quote of value
        after_key = idx + len(key)
        while after_key < len(json_str) and json_str[after_key] in ": \t":
            after_key += 1
        if after_key >= len(json_str) or json_str[after_key] != '"':
            return json_str
        value_start = after_key + 1  # first char of value (after opening ")
        # Find closing quote, respecting \"
        i = value_start
        while i < len(json_str):
            if json_str[i] == "\\" and i + 1 < len(json_str):
                i += 2
                continue
            if json_str[i] == '"':
                value_end = i  # exclusive end of value
                return (
                    json_str[:value_start]
                    + _MESSAGE_VALUE_COLOR
                    + json_str[value_start:value_end]
                    + _RESET
                    + json_str[value_end:]
                )
            i += 1
    except Exception:
        pass
    return json_str


def _unescape_traceback_in_json(json_str: str) -> str:
    """
    Find the "traceback" key's string value in the JSON and replace escaped newlines
    (\\n) with real newlines so the value displays on multiple lines. The traceback
    stays as the value of the key; output is multi-line but still one JSON object.
    """
    try:
        key = '"traceback"'
        idx = json_str.find(key)
        if idx == -1:
            return json_str
        after_key = idx + len(key)
        while after_key < len(json_str) and json_str[after_key] in ": \t":
            after_key += 1
        if after_key >= len(json_str) or json_str[after_key] != '"':
            return json_str
        value_start = after_key + 1
        i = value_start
        while i < len(json_str):
            if json_str[i] == "\\" and i + 1 < len(json_str):
                i += 2
                continue
            if json_str[i] == '"':
                value_end = i
                # Replace \\n with real newline only inside the traceback value
                inner = json_str[value_start:value_end]
                inner = inner.replace("\\n", "\n")
                return json_str[:value_start] + inner + json_str[value_end:]
            i += 1
    except Exception:
        pass
    return json_str


def _format_record_with_traceback(
    record: logging.LogRecord,
    levelname: str,
    color: str,
    use_color: bool,
) -> str | None:
    """
    If record.msg is JSON with a non-empty traceback, return the same JSON with
    the traceback value unescaped (real newlines) so it displays readably while
    still being the value of the "traceback" key.
    """
    msg = getattr(record, "msg", None)
    if not isinstance(msg, str) or not msg.strip():
        return None
    try:
        data = json.loads(msg)
        if not isinstance(data.get("traceback"), str) or not data["traceback"].strip():
            return None
    except Exception:
        return None
    # Unescape newlines in the traceback value so it prints on multiple lines
    json_with_newlines = _unescape_traceback_in_json(msg)
    if use_color:
        body = _highlight_message_value(json_with_newlines)
    else:
        body = json_with_newlines
    return f"{color}{_BOLD}{levelname}{_RESET}    {body}" if use_color else f"{levelname}    {body}"


class ColoredJsonFormatter(logging.Formatter):
    """Format log records with colored level and highlighted JSON "message" value when output is a TTY."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._use_color = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        levelname = record.levelname
        color = _LEVEL_COLORS.get(levelname, _RESET)
        # If message is JSON with traceback, expand traceback to multiple lines
        multi = _format_record_with_traceback(record, levelname, color, self._use_color)
        if multi is not None:
            return multi
        if not self._use_color:
            return base
        # Color the level and highlight the JSON message value
        if levelname and base.startswith(levelname):
            rest = base[len(levelname) :]
            if getattr(record, "msg", None) and isinstance(record.msg, str):
                highlighted_msg = _highlight_message_value(record.msg)
                return f"{color}{_BOLD}{levelname}{_RESET}    {highlighted_msg}"
            return f"{color}{_BOLD}{levelname}{_RESET}{rest}"
        return base

LogLevel = Literal["info", "warning", "debug", "error"]
VALID_LEVELS: tuple[LogLevel, ...] = ("info", "warning", "debug", "error")


def _caller_location() -> str:
    """Return module path where log_json was called, e.g. src.backend.ai_backend.routers.common."""
    try:
        for frame_info in inspect.stack():
            module = frame_info.frame.f_globals.get("__name__", "")
            # Skip frames inside this module so we get the actual caller (e.g. common.py, clarify_once.py)
            if module and not module.startswith("ai_backend.log_utils"):
                return f"src.backend.{module}"
    except Exception:
        pass
    return "src.backend.unknown"


def log_json(
    source: str,
    level: LogLevel,
    message: str,
    user_id: Optional[UUID] = None,
    traceback: Optional[str] = None,
) -> None:
    """
    Emit a single log line as a JSON object.

    Args:
        source: Feature name (e.g. auth, ocr, clarify_step_by_step).
        level: info, warning, debug, or error.
        message: Description of what is happening; for errors use str(e).
        user_id: User UUID when known; None when unknown (e.g. before auth).
        traceback: Full traceback string only when level is "error"; otherwise None.

    Log line format: one JSON object per line. "location" is set automatically to the
    calling module path (e.g. src.backend.ai_backend.routers.common).
    """
    if level not in VALID_LEVELS:
        try:
            _LOGGER.warning(
                "log_json invalid level=%s (source=%s); using info",
                level,
                source,
            )
        except Exception:
            pass
        level = "info"

    # Per SKILL: traceback only for errors; otherwise null
    tb_value: Optional[str] = traceback if level == "error" else None

    payload = {
        "level": level,
        "source": source,
        "message": message,
        "location": _caller_location(),
        "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "user_id": str(user_id) if user_id is not None else None,
        "traceback": tb_value,
    }

    try:
        json_message = json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        try:
            fallback = json.dumps(
                {
                    "source": "log_utils",
                    "location": "src.backend.ai_backend.log_utils",
                    "level": "error",
                    "message": f"JSON serialization failed: {e!s}",
                    "user_id": None,
                    "traceback": None,
                },
                ensure_ascii=False,
            )
            _LOGGER.error(fallback)
        except Exception:
            _LOGGER.error("log_json: serialization failed and fallback failed")
        return

    try:
        if level == "info":
            _LOGGER.info(json_message)
        elif level == "warning":
            _LOGGER.warning(json_message)
        elif level == "error":
            _LOGGER.error(json_message)
        elif level == "debug":
            _LOGGER.debug(json_message)
        else:
            _LOGGER.info(json_message)
    except Exception as e:
        try:
            logging.getLogger(__name__).warning(
                "log_json emit failed: %s (source=%s)", e, source
            )
        except Exception:
            pass
