/// One row matching a JSON object `{ "step": "...", "score": 1 }` (Punctaj column).
class ExamSolutionStepRow {
  /// Creates a row with [step] (Pas) and optional [score] (Punctaj).
  const ExamSolutionStepRow({
    required this.step,
    this.score,
  });

  /// Step text for the **Pas** column (may contain markdown / LaTeX).
  final String step;

  /// Numeric punctaj for the **Punctaj** column (JSON `score` or `punctaj`).
  final double? score;
}
