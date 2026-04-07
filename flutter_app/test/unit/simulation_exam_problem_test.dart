import "package:flutter_test/flutter_test.dart";
import "package:profu_app/models/simulation_exam_problem.dart";

void main() {
  group("SimulationExamProblem", () {
    test("maxPointsForSubject Bac layout", () {
      expect(SimulationExamProblem.maxPointsForSubject(1), 5);
      expect(SimulationExamProblem.maxPointsForSubject(2), 15);
      expect(SimulationExamProblem.maxPointsForSubject(3), 15);
      expect(SimulationExamProblem.maxPointsForSubject(99), 0);
    });

    test("sectionTitle Romanian labels", () {
      expect(SimulationExamProblem.sectionTitle(1), "Subiectul I");
      expect(SimulationExamProblem.sectionTitle(2), "Subiectul II");
      expect(SimulationExamProblem.sectionTitle(3), "Subiectul III");
      expect(SimulationExamProblem.sectionTitle(4), "Subiect 4");
    });

    test("toSimilarityQueryText joins statement and items", () {
      final SimulationExamProblem p = SimulationExamProblem(
        rowId: 1,
        examProblemId: 10,
        subjectNumber: 2,
        problemNumber: 1,
        orderIndex: 1,
        statement: "  Enunț principal  ",
        items: <String>["  a) primul  ", "", "b) al doilea"],
      );
      expect(
        p.toSimilarityQueryText(),
        "Enunț principal\na) primul\nb) al doilea",
      );
    });

    test("toSimilarityQueryText empty when no content", () {
      final SimulationExamProblem p = SimulationExamProblem(
        rowId: 1,
        examProblemId: 1,
        subjectNumber: 1,
        problemNumber: 1,
        orderIndex: 0,
        statement: "   ",
        items: <String>["", "  "],
      );
      expect(p.toSimilarityQueryText(), "");
    });

    test("hasMarkingGuide respects rows and markdown", () {
      final SimulationExamProblem empty = SimulationExamProblem(
        rowId: 1,
        examProblemId: 1,
        subjectNumber: 1,
        problemNumber: 1,
        orderIndex: 0,
        statement: "s",
      );
      expect(empty.hasMarkingGuide, false);

      final SimulationExamProblem withMd = SimulationExamProblem(
        rowId: 1,
        examProblemId: 1,
        subjectNumber: 1,
        problemNumber: 1,
        orderIndex: 0,
        statement: "s",
        markingMarkdownFallback: " # x ",
      );
      expect(withMd.hasMarkingGuide, true);
    });
  });
}
