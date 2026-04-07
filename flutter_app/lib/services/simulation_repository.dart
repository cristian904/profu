import "package:flutter/foundation.dart";
import "package:supabase_flutter/supabase_flutter.dart";

import "../data/parsing/simulation_join_rows_mapper.dart";
import "../models/simulation_exam_problem.dart";
import "../models/simulation_history_entry.dart";

export "../models/simulation_exam_problem.dart";
export "../models/simulation_history_entry.dart";

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
            "id, exam_problem_id, subject_number, problem_number, order_index, student_score, "
            "exam_problems(statement, topic, choices, items, solution, "
            "scoring_scales(solution, order_index))",
          )
          .eq("exam_simulation_id", simulationId)
          .order("subject_number", ascending: true)
          .order("problem_number", ascending: true);

      final List<dynamic> rows = response as List<dynamic>;
      final List<SimulationExamProblem> out = simulationProblemsFromJoinRows(rows);

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

  /// Loads finished simulations with scores for the signed-in user (oldest first).
  ///
  /// Rows must have both [finished_at] and [student_score] set (submitted scoring).
  Future<List<SimulationHistoryEntry>> fetchScoredSimulationHistoryForCurrentUser() async {
    final String? userId = _client.auth.currentUser?.id;
    if (userId == null || userId.isEmpty) {
      throw Exception("Trebuie sa fii autentificat.");
    }

    try {
      if (kDebugMode) {
        debugPrint("[SimulationRepository] fetchScoredSimulationHistoryForCurrentUser start");
      }

      final dynamic response = await _client
          .from("exam_simulations")
          .select("id, student_score, finished_at, school_subject")
          .eq("auth_user_id", userId)
          .not("finished_at", "is", null)
          .not("student_score", "is", null)
          .order("finished_at", ascending: true);

      final List<dynamic> rows = response as List<dynamic>;
      final List<SimulationHistoryEntry> out = <SimulationHistoryEntry>[];
      for (final dynamic raw in rows) {
        final Map<String, dynamic> row = Map<String, dynamic>.from(raw as Map);
        final SimulationHistoryEntry? e = SimulationHistoryEntry.fromSupabaseRow(row);
        if (e != null) {
          out.add(e);
        }
      }

      if (kDebugMode) {
        debugPrint(
          "[SimulationRepository] fetchScoredSimulationHistoryForCurrentUser loaded count=${out.length}",
        );
      }
      return out;
    } catch (e, st) {
      if (kDebugMode) {
        debugPrint(
          "[SimulationRepository] fetchScoredSimulationHistoryForCurrentUser error: $e\n$st",
        );
      }
      rethrow;
    }
  }
}
