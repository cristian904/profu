import "exam_solution_step_row.dart";

/// One problem line in an active simulation (joined with [exam_problems]).
class SimulationExamProblem {
  /// Creates a row for UI display.
  SimulationExamProblem({
    required this.rowId,
    required this.examProblemId,
    required this.subjectNumber,
    required this.problemNumber,
    required this.orderIndex,
    required this.statement,
    this.topic,
    List<String>? items,
    List<ExamSolutionStepRow>? markingStepRows,
    this.markingMarkdownFallback,
  })  : items = List<String>.unmodifiable(items ?? <String>[]),
        markingStepRows = List<ExamSolutionStepRow>.unmodifiable(
          markingStepRows ?? <ExamSolutionStepRow>[],
        );

  /// exam_simulation_problems.id
  final int rowId;

  /// Linked `exam_problems.id` (random pick per slot when the simulation was created).
  final int examProblemId;
  final int subjectNumber;
  final int problemNumber;
  final int? orderIndex;
  final String statement;
  final String? topic;

  /// Sub-items for Subiectul II/III (e.g. demonstrează / calculează), from JSONB [items].
  final List<String> items;

  /// Parsed barem rows (Pas + Punctaj per list item) from [solution] JSONB and/or `scoring_scales`.
  final List<ExamSolutionStepRow> markingStepRows;

  /// Non-tabular barem / prose when [markingStepRows] is empty.
  final String? markingMarkdownFallback;

  /// True if any marking content is available for post-exam display.
  bool get hasMarkingGuide {
    if (markingStepRows.isNotEmpty) {
      return true;
    }
    final String? s = markingMarkdownFallback?.trim();
    return s != null && s.isNotEmpty;
  }

  /// Max points for Bac layout: Subiectul I = 5p each, II/III = 15p each.
  static int maxPointsForSubject(int subjectNumber) {
    if (subjectNumber == 1) {
      return 5;
    }
    if (subjectNumber == 2 || subjectNumber == 3) {
      return 15;
    }
    return 0;
  }

  /// Romanian section title for the exam structure.
  static String sectionTitle(int subjectNumber) {
    switch (subjectNumber) {
      case 1:
        return "Subiectul I";
      case 2:
        return "Subiectul II";
      case 3:
        return "Subiectul III";
      default:
        return "Subiect $subjectNumber";
    }
  }
}
