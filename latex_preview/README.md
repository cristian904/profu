# LaTeX / Markdown Preview

Small Flutter app to preview markdown and LaTeX using the same rendering as the main Profu app (`flutter_markdown` + `flutter_math_fork`).

**Use case:** Paste the output of `validate_latex.py --fix --output-corrected` or `format_formulas.py` and see how it will render in the app.

## Run

```bash
cd latex_preview
flutter pub get
flutter run
```

## Usage

1. Paste your markdown/LaTeX text (e.g. from `*_corrected.txt` or `*_formatted.txt`) into the input box.
2. Tap **Preview** to render it below.
3. Inline math: `$...$`. Display math: `$$...$$`. Invalid LaTeX shows in red.
