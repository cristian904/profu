import "package:flutter_test/flutter_test.dart";
import "package:profu_app/pages/simulation_similar_problems_policy.dart";

void main() {
  group("simulariShowSimilarProblemsIcon", () {
    test("hidden while live exam in progress", () {
      expect(
        simulariShowSimilarProblemsIcon(
          examSessionEnded: false,
          viewingPastSimulation: false,
        ),
        false,
      );
    });

    test("shown after live exam finished", () {
      expect(
        simulariShowSimilarProblemsIcon(
          examSessionEnded: true,
          viewingPastSimulation: false,
        ),
        true,
      );
    });

    test("shown when reviewing simulation from Istoric", () {
      expect(
        simulariShowSimilarProblemsIcon(
          examSessionEnded: false,
          viewingPastSimulation: true,
        ),
        true,
      );
    });

    test("shown when Istoric row also has session-ended flag set", () {
      expect(
        simulariShowSimilarProblemsIcon(
          examSessionEnded: true,
          viewingPastSimulation: true,
        ),
        true,
      );
    });
  });

  group("simulariSimilarProblemsConversationPrefix", () {
    test("live flow uses Simulare", () {
      expect(
        simulariSimilarProblemsConversationPrefix(viewingPastSimulation: false),
        "Simulare",
      );
    });

    test("Istoric flow uses Istoric simulare", () {
      expect(
        simulariSimilarProblemsConversationPrefix(viewingPastSimulation: true),
        "Istoric simulare",
      );
    });
  });
}
