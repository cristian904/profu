/// One finished simulation with a stored total score (for Istoric chart).
class SimulationHistoryEntry {
  /// Creates a history row for charts and lists.
  const SimulationHistoryEntry({
    required this.simulationId,
    required this.finishedAt,
    required this.studentScore,
    this.schoolSubject,
  });

  /// Primary key of [exam_simulations].
  final int simulationId;

  /// When the user submitted scoring (server-side timestamp).
  final DateTime finishedAt;

  /// Total points persisted after submit (sum of per-problem or self total).
  final double studentScore;

  /// Subject key from DB (e.g. `mate`), if present.
  final String? schoolSubject;

  /// Parses one Supabase/PostgREST row; returns null if required fields are missing.
  static SimulationHistoryEntry? fromSupabaseRow(Map<String, dynamic> row) {
    final dynamic idRaw = row["id"];
    final int? simulationId = idRaw is int ? idRaw : int.tryParse(idRaw?.toString() ?? "");
    if (simulationId == null) {
      return null;
    }

    final dynamic finishedRaw = row["finished_at"];
    if (finishedRaw == null) {
      return null;
    }
    final DateTime? finishedAt = DateTime.tryParse(finishedRaw.toString());
    if (finishedAt == null) {
      return null;
    }

    final dynamic scoreRaw = row["student_score"];
    final double? studentScore = scoreRaw is num
        ? scoreRaw.toDouble()
        : double.tryParse(scoreRaw?.toString() ?? "");
    if (studentScore == null) {
      return null;
    }

    final dynamic subj = row["school_subject"];
    final String? schoolSubject = subj == null ? null : subj.toString();

    return SimulationHistoryEntry(
      simulationId: simulationId,
      finishedAt: finishedAt,
      studentScore: studentScore,
      schoolSubject: schoolSubject,
    );
  }
}
