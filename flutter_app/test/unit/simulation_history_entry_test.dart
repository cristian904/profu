import "package:flutter_test/flutter_test.dart";
import "package:profu_app/models/simulation_history_entry.dart";

void main() {
  group("SimulationHistoryEntry.fromSupabaseRow", () {
    test("parses valid row", () {
      final SimulationHistoryEntry? e = SimulationHistoryEntry.fromSupabaseRow(<String, dynamic>{
        "id": 42,
        "finished_at": "2026-04-01T14:30:00.000Z",
        "student_score": 67.5,
        "school_subject": "mate",
      });
      expect(e, isNotNull);
      expect(e!.simulationId, 42);
      expect(e.studentScore, 67.5);
      expect(e.schoolSubject, "mate");
      expect(e.finishedAt.year, 2026);
    });

    test("returns null when score missing", () {
      final SimulationHistoryEntry? e = SimulationHistoryEntry.fromSupabaseRow(<String, dynamic>{
        "id": 1,
        "finished_at": "2026-01-01T00:00:00.000Z",
      });
      expect(e, isNull);
    });
  });
}
