"""
Romanian prompts for markdown + YAML structured extraction.
"""
from __future__ import annotations

EXTRACT_STRUCTURED_PROBLEMS_PROMPT = """Primești markdown cu enunțuri de bacalaureat mate. Documentul poate avea doar s1, doar s2, doar s3 sau mai multe subiecte.

Returnează **DOAR** markdown (nu JSON) în formatul:

---
format: exam-parser-structured-problems-v1
# dacă documentul are un singur subiect, adaugă:
# subject: s1
---

## Subject s1
## Problem
```yaml
number: 1
subject: mate
topic: "..."
difficulty: medium
statement: |
  <copie exactă din sursă, caracter cu caracter>
choices: []
```

## Subject s2
## Problem
```yaml
number: 1
subject: mate
topic: "..."
difficulty: medium
statement: |
  <copie exactă din sursă, caracter cu caracter>
choices: []
items:
  - |
    a) <copie exactă>
  - |
    b) <copie exactă>
  - |
    c) <copie exactă>
```

Reguli OBLIGATORII:
1) **COPIE EXACTĂ, caracter-cu-caracter** pentru `statement` și `items`.
2) Nu reformula, nu corecta, nu traduce.
3) `items` apare doar când subiectul/problema are subpuncte în sursă.
4) `choices` rămâne listă YAML (de obicei `[]`).
5) Pentru fiecare subiect prezent în sursă, include secțiunea lui (`s1`/`s2`/`s3`).
6) Folosește fence ` ```yaml ` (sau YAML/yml). Închide fiecare fence corect.

Markdown de procesat:
"""


EXTRACT_STRUCTURED_SOLUTIONS_PROMPT = """Primești markdown din barem/rezolvare bac mate. Documentul poate avea s1, s2, s3 sau orice subset.

Returnează **DOAR** markdown (nu JSON), format:

---
format: exam-parser-structured-solutions-v1
# dacă documentul are un singur subiect:
# subject: s1
---

## Subject s1
## Solution
```yaml
number: 1
subject: mate
topic: "..."
difficulty: medium
statement: |
  <copie exactă enunț>
solution_steps: |
  <copie exactă soluție completă pentru s1, caracter cu caracter>
```

## Subject s2
## Solution
```yaml
number: 1
subject: mate
topic: "..."
difficulty: medium
statement: |
  <copie exactă enunț>
item_solutions:
  - item: a
    solution_steps:
      - step: |
          <copie exactă pas>
        score: 0.5
      - step: |
          <copie exactă pas>
        score: 1
  - item: b
    solution_steps:
      - step: |
          <copie exactă pas>
        score: 0.5
```

Reguli OBLIGATORII:
1) Pentru **s1**, `solution_steps` este **string** (nu listă).
2) Pentru **s2/s3**, folosește `item_solutions` listă cu `{item, solution_steps}`.
3) Pentru fiecare `item`, `solution_steps` este listă de obiecte `{step, score}`.
4) `statement`, `step` și textul din `solution_steps` trebuie copiate **caracter-cu-caracter** din sursă.
5) Nu folosi câmpul `items` în fișierele de solutions.
6) Include doar subiectele prezente în sursă.
7) Liniile sub `step: |` trebuie indentate; nu lăsa formule la coloana 0.

Markdown de procesat:
"""
