import "package:flutter/foundation.dart";
import "package:supabase_flutter/supabase_flutter.dart";

import "../models/exam_marking_display.dart";
import "../models/exam_solution_step_row.dart";
import "../utils/exam_solution_steps_parse.dart";

/// Parses nested `scoring_scales` from PostgREST into ordered markdown chunks.
List<String> _parseScoringScaleChunks(dynamic raw) {
  if (raw == null) {
    return <String>[];
  }
  if (raw is! List) {
    if (kDebugMode) {
      debugPrint("[SimulationRepository] scoring_scales is not a list: ${raw.runtimeType}");
    }
    return <String>[];
  }

  int orderKey(Map<String, dynamic> m) {
    final dynamic o = m["order_index"];
    if (o is num) {
      return o.toInt();
    }
    return 0;
  }

  final List<Map<String, dynamic>> rows = <Map<String, dynamic>>[];
  for (final dynamic e in raw) {
    if (e is Map) {
      rows.add(Map<String, dynamic>.from(e));
    }
  }
  rows.sort((Map<String, dynamic> a, Map<String, dynamic> b) {
    return orderKey(a).compareTo(orderKey(b));
  });

  final List<String> out = <String>[];
  for (final Map<String, dynamic> m in rows) {
    final String? sol = m["solution"] as String?;
    final String t = sol?.trim() ?? "";
    if (t.isNotEmpty) {
      out.add(t);
    }
  }
  return out;
}

/// Parses [exam_problems.items] JSONB into non-empty strings (Subiectul II/III sub-tasks).
List<String> _parseProblemItems(dynamic raw) {
  if (raw == null) {
    return <String>[];
  }
  if (raw is! List) {
    if (kDebugMode) {
      debugPrint("[SimulationRepository] items is not a list, ignoring: ${raw.runtimeType}");
    }
    return <String>[];
  }
  final List<String> out = <String>[];
  for (final dynamic e in raw) {
    if (e == null) {
      continue;
    }
    final String s = e.toString().trim();
    if (s.isNotEmpty) {
      out.add(s);
    }
  }
  return out;
}

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

/// Loads simulation data from Supabase for the Simulari feature.
class SimulationRepository {
  /// Creates repository using [client] or the global Supabase client.
  SimulationRepository({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;

  /// Ensures the simulation exists and belongs to the signed-in user, then returns its problems.
  Future<List<SimulationExamProblem>> fetchSimulationProblemsForCurrentUser({
    required int simulationId,
  }) async {
    final String? userId = _client.auth.currentUser?.id;
    if (userId == null || userId.isEmpty) {
      throw Exception("Trebuie sa fii autentificat.");
    }

    try {
      final dynamic simRaw = await _client
          .from("exam_simulations")
          .select("id, auth_user_id")
          .eq("id", simulationId)
          .maybeSingle();

      if (simRaw == null) {
        throw Exception("Simularea nu a fost gasita.");
      }

      final Map<String, dynamic> sim = Map<String, dynamic>.from(simRaw as Map);
      final String? owner = sim["auth_user_id"]?.toString();
      if (owner != userId) {
        throw Exception("Nu ai acces la aceasta simulare.");
      }

      final dynamic response = await _client
          .from("exam_simulation_problems")
          .select(
            "id, exam_problem_id, subject_number, problem_number, order_index, "
            "exam_problems(statement, topic, choices, items, solution, "
            "scoring_scales(solution, order_index))",
          )
          .eq("exam_simulation_id", simulationId)
          .order("subject_number", ascending: true)
          .order("problem_number", ascending: true);

      final List<dynamic> rows = response as List<dynamic>;
      final List<SimulationExamProblem> out = <SimulationExamProblem>[];

      for (final dynamic raw in rows) {
        final Map<String, dynamic> row = Map<String, dynamic>.from(raw as Map);
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
          items = _parseProblemItems(m["items"]);
          scaleChunks = _parseScoringScaleChunks(m["scoring_scales"]);
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
            "[SimulationRepository] No marking UI for simulation line "
            "subiect=${row["subject_number"]} problema=${row["problem_number"]} "
            "exam_problem_id=${row["exam_problem_id"]} solution_type=${solutionRaw.runtimeType}",
          );
        }

        out.add(
          SimulationExamProblem(
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
          ),
        );
      }

      if (kDebugMode) {
        debugPrint(
          "[SimulationRepository] Loaded ${out.length} problems for simulation_id=$simulationId",
        );
      }
      return out;
    } catch (e, st) {
      if (kDebugMode) {
        debugPrint("[SimulationRepository] fetchSimulationProblemsForCurrentUser error: $e\n$st");
      }
      rethrow;
    }
  }
}
