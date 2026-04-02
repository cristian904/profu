import "package:flutter/foundation.dart";

import "../../models/exam_marking_display.dart";
import "../../models/simulation_exam_problem.dart";
import "../../utils/exam_solution_steps_parse.dart";
import "simulation_problems_parse.dart";

/// Maps one PostgREST join row (`exam_simulation_problems` + nested `exam_problems`) to [SimulationExamProblem].
SimulationExamProblem simulationExamProblemFromJoinRow(Map<String, dynamic> row) {
  final dynamic ep = row["exam_problems"];
  String statement = "";
  String? topic;
  List<String> items = <String>[];
  List<String> scaleChunks = <String>[];
  dynamic solutionRaw;
  if (ep is Map) {
    final Map<String, dynamic> m = Map<String, dynamic>.from(ep);
    statement = (m["statement"] as String?)?.trim() ?? "";
    topic = m["topic"] as String?;
    items = parseProblemItems(m["items"]);
    scaleChunks = parseScoringScaleChunks(m["scoring_scales"]);
    solutionRaw = m["solution"];
  }
  if (statement.isEmpty) {
    statement = "(Enunt indisponibil)";
  }

  final ExamMarkingDisplay marking = computeExamMarkingDisplay(
    solutionJson: solutionRaw,
    scoringScaleChunks: scaleChunks,
  );

  if (kDebugMode &&
      marking.tableRows.isEmpty &&
      (marking.markdown == null || marking.markdown!.trim().isEmpty) &&
      solutionRaw != null) {
    debugPrint(
      "[simulation_join_rows_mapper] No marking UI for simulation line "
      "subiect=${row["subject_number"]} problema=${row["problem_number"]} "
      "exam_problem_id=${row["exam_problem_id"]} solution_type=${solutionRaw.runtimeType}",
    );
  }

  return SimulationExamProblem(
    rowId: (row["id"] as num).toInt(),
    examProblemId: (row["exam_problem_id"] as num).toInt(),
    subjectNumber: (row["subject_number"] as num).toInt(),
    problemNumber: (row["problem_number"] as num).toInt(),
    orderIndex: row["order_index"] != null ? (row["order_index"] as num).toInt() : null,
    statement: statement,
    topic: topic,
    items: items,
    markingStepRows: marking.tableRows,
    markingMarkdownFallback: marking.markdown,
  );
}

/// Maps a list of PostgREST rows to [SimulationExamProblem] list.
List<SimulationExamProblem> simulationProblemsFromJoinRows(List<dynamic> rows) {
  final List<SimulationExamProblem> out = <SimulationExamProblem>[];
  for (final dynamic raw in rows) {
    final Map<String, dynamic> row = Map<String, dynamic>.from(raw as Map);
    out.add(simulationExamProblemFromJoinRow(row));
  }
  return out;
}
