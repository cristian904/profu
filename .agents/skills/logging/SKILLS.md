---
name: logging
description: Use this when you create log statements. This will explain what information should the logs contain, what to log and what not to log.
---

# Logging

## Instructions
The log message will be a JSON object with the following attributes:
- source: name of the feature where the log/error occurred (auth, langfuse, clarify_step_by_step)
- location: module path where the log originated (e.g. src.backend.ai_backend.routers.common)
- level: info/warning/debug/error (debug messages should only be written when the agent does
debugging, these will be cleared when debugging is done)
- message: Description of what is happening (in case of error just print here the str(e))
- timestamp: UTC datetime when the log was emitted, truncated to seconds (e.g. 2026-03-15T11:27:26)
- user_id: the id of the user making the call
- traceback: In case of error include the entire error traceback, if the level is not "error"
this should be null.

## Examples
```json
{
    "source": "clarify_step_by_step",
    "location": "src.backend.ai_backend.routers.clarify_with_steps",
    "level": "info/debug/warning/error",
    "message": "description",
    "timestamp": "2026-03-15T11:27:26",
    "user_id": "user uuid",
    "traceback": "full traceback in case of error"
}
```
