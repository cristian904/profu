import "package:flutter_test/flutter_test.dart";
import "package:profu_app/data/parsing/simulation_problems_parse.dart";

void main() {
  group("parseProblemItems", () {
    test("null returns empty", () {
      expect(parseProblemItems(null), isEmpty);
    });

    test("non-list returns empty", () {
      expect(parseProblemItems("x"), isEmpty);
    });

    test("collects trimmed non-empty strings", () {
      expect(
        parseProblemItems(<dynamic>["  a ", "", null, 42]),
        <String>["a", "42"],
      );
    });
  });

  group("parseScoringScaleChunks", () {
    test("null returns empty", () {
      expect(parseScoringScaleChunks(null), isEmpty);
    });

    test("non-list returns empty", () {
      expect(parseScoringScaleChunks(<String, dynamic>{}), isEmpty);
    });

    test("orders by order_index and extracts solution text", () {
      final List<dynamic> raw = <dynamic>[
        <String, dynamic>{"order_index": 2, "solution": "  second  "},
        <String, dynamic>{"order_index": 1, "solution": "first"},
        <String, dynamic>{"order_index": 3, "solution": ""},
      ];
      expect(parseScoringScaleChunks(raw), <String>["first", "second"]);
    });
  });
}
