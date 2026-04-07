import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:profu_app/services/suggest_similar_problems_api.dart";

void main() {
  group("parseSuccessResponseBody", () {
    test("returns null for invalid JSON", () {
      expect(parseSuccessResponseBody("not json"), isNull);
    });

    test("returns null when root is not an object", () {
      expect(parseSuccessResponseBody(json.encode(<String>[])), isNull);
    });

    test("parses message and statements", () {
      final SuggestSimilarProblemsResult? r = parseSuccessResponseBody(
        json.encode(<String, dynamic>{
          "message": "Uite 2 probleme",
          "problems": <Map<String, dynamic>>[
            <String, dynamic>{"statement": r"$x^2$"},
            <String, dynamic>{"statement": "plain"},
          ],
        }),
      );
      expect(r, isNotNull);
      expect(r!.message, "Uite 2 probleme");
      expect(r.statements, <String>[r"$x^2$", "plain"]);
    });

    test("parseSuccessResponseMap defaults message when missing", () {
      final SuggestSimilarProblemsResult r = parseSuccessResponseMap(<String, dynamic>{
        "problems": <dynamic>[],
      });
      expect(r.message, "Nu am găsit probleme similare.");
      expect(r.statements, isEmpty);
    });

    test("parseSuccessResponseMap tolerates non-map problem entries", () {
      final SuggestSimilarProblemsResult r = parseSuccessResponseMap(<String, dynamic>{
        "message": "ok",
        "problems": <dynamic>[
          "bad",
          <String, dynamic>{"statement": "good"},
        ],
      });
      expect(r.statements, <String>["", "good"]);
    });
  });
}
