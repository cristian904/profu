import "package:flutter_test/flutter_test.dart";
import "package:profu_app/data/parsing/simulation_join_rows_mapper.dart";
import "package:profu_app/models/simulation_exam_problem.dart";

void main() {
  group("simulationExamProblemFromJoinRow", () {
    test("fills statement topic items and marking from nested exam_problems", () {
      final SimulationExamProblem p = simulationExamProblemFromJoinRow(<String, dynamic>{
        "id": 1,
        "exam_problem_id": 99,
        "subject_number": 2,
        "problem_number": 1,
        "order_index": 0,
        "exam_problems": <String, dynamic>{
          "statement": "  Demo  ",
          "topic": "Alg",
          "items": <dynamic>["a", "b"],
          "scoring_scales": <dynamic>[
            <String, dynamic>{"order_index": 1, "solution": "| Pas | Punctaj |\n| --- | --- |\n| X | 1 |"},
          ],
          "solution": <dynamic>[
            <String, dynamic>{"step": "S1", "score": 1},
          ],
        },
      });
      expect(p.statement, "Demo");
      expect(p.topic, "Alg");
      expect(p.items, <String>["a", "b"]);
      expect(p.markingStepRows, isNotEmpty);
      expect(p.rowId, 1);
      expect(p.examProblemId, 99);
    });

    test("uses fallback statement when missing", () {
      final SimulationExamProblem p = simulationExamProblemFromJoinRow(<String, dynamic>{
        "id": 1,
        "exam_problem_id": 1,
        "subject_number": 1,
        "problem_number": 1,
        "order_index": null,
        "exam_problems": <String, dynamic>{},
      });
      expect(p.statement, "(Enunt indisponibil)");
      expect(p.orderIndex, isNull);
    });

    test("null exam_problems uses unavailable statement", () {
      final SimulationExamProblem p = simulationExamProblemFromJoinRow(<String, dynamic>{
        "id": 1,
        "exam_problem_id": 1,
        "subject_number": 1,
        "problem_number": 1,
        "order_index": 0,
      });
      expect(p.statement, "(Enunt indisponibil)");
    });
  });

  group("simulationProblemsFromJoinRows", () {
    test("maps multiple rows", () {
      final List<SimulationExamProblem> list = simulationProblemsFromJoinRows(<dynamic>[
        <String, dynamic>{
          "id": 1,
          "exam_problem_id": 1,
          "subject_number": 1,
          "problem_number": 1,
          "order_index": 0,
          "exam_problems": <String, dynamic>{"statement": "A"},
        },
        <String, dynamic>{
          "id": 2,
          "exam_problem_id": 2,
          "subject_number": 1,
          "problem_number": 2,
          "order_index": 1,
          "exam_problems": <String, dynamic>{"statement": "B"},
        },
      ]);
      expect(list.length, 2);
      expect(list[0].statement, "A");
      expect(list[1].statement, "B");
    });
  });
}
