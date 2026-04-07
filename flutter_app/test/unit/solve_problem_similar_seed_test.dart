import "package:flutter_test/flutter_test.dart";
import "package:profu_app/pages/simulation_similar_problems_policy.dart";
import "package:profu_app/pages/solve_problem_page.dart";
import "package:profu_app/models/simulation_exam_problem.dart";

void main() {
  group("SimilarProblemsSeed", () {
    test("carries message, statements, and conversation title", () {
      const SimilarProblemsSeed seed = SimilarProblemsSeed(
        message: "Uite 1 probleme",
        statements: <String>["stmt"],
        conversationTitle: "Simulare · Subiectul I, problema 1",
      );
      expect(seed.message, "Uite 1 probleme");
      expect(seed.statements, <String>["stmt"]);
      expect(seed.conversationTitle, contains("Subiectul I"));
    });

    test("Istoric title matches policy prefix + section label", () {
      final String prefix = simulariSimilarProblemsConversationPrefix(
        viewingPastSimulation: true,
      );
      final String title =
          "$prefix · ${SimulationExamProblem.sectionTitle(2)}, problema 1";
      expect(title, "Istoric simulare · Subiectul II, problema 1");
    });
  });
}
