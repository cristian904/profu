"""
AI domain services (one package per major product capability).

- ``clarify_once`` — direct answers (/clarify/once-stream)
- ``clarify_with_steps`` — guided step-by-step learning (/clarify/step-by-step-stream)
- ``solve_problem`` — problem solving with hints and OCR
- ``simulari`` — exam simulations (/simulari)

Shared helpers live under ``ai_backend.common``.

Each LangGraph service typically has ``graph.py`` (``TypedDict`` state, routing, compile) and
``nodes.py`` (node callables; imported from ``graph.py`` after state is defined).
"""
