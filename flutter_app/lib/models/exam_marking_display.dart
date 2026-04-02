import "exam_solution_step_row.dart";

/// Result of parsing `exam_problems.solution` + optional `scoring_scales` for post-exam UI.
///
/// Either a **table** (list of `{step, score}` objects) or **plain markdown** (string
/// `solution_steps`), not both from the same solution field.
class ExamMarkingDisplay {
  /// Creates marking content for the simulation card.
  const ExamMarkingDisplay({
    required this.tableRows,
    this.markdown,
  });

  /// Non-empty when `solution` was a JSON **list** of steps (or barem table from scales).
  final List<ExamSolutionStepRow> tableRows;

  /// Non-empty when `solution` was a **string** (or only unstructured barem text).
  final String? markdown;
}
