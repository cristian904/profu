import "package:flutter_test/flutter_test.dart";
import "package:profu_app/models/exam_solution_step_row.dart";
import "package:profu_app/utils/exam_solution_steps_parse.dart";

void main() {
  group("unwrapSolutionPayload", () {
    test("returns null for null", () {
      expect(unwrapSolutionPayload(null), isNull);
    });

    test("unwraps through barem key", () {
      final dynamic u = unwrapSolutionPayload(<String, dynamic>{
        "barem": <dynamic>[
          <String, dynamic>{"step": "B", "score": 1},
        ],
      });
      expect(u, isA<List<dynamic>>());
    });

    test("unwraps nested solution_steps", () {
      final dynamic raw = <String, dynamic>{
        "solution_steps": <dynamic>[
          <String, dynamic>{"step": "A", "score": 1},
        ],
      };
      final dynamic u = unwrapSolutionPayload(raw);
      expect(u, isA<List<dynamic>>());
    });
  });

  group("solutionListToTableRows", () {
    test("maps step and score fields", () {
      final List<ExamSolutionStepRow> rows = solutionListToTableRows(<dynamic>[
        <String, dynamic>{"step": "Pas 1", "score": 2},
        <String, dynamic>{"solution": "Alt", "punctaj": "1,5p"},
      ]);
      expect(rows.length, 2);
      expect(rows[0].step, "Pas 1");
      expect(rows[0].score, 2);
      expect(rows[1].score, closeTo(1.5, 0.001));
    });

    test("skips map items without displayable step", () {
      final List<ExamSolutionStepRow> rows = solutionListToTableRows(<dynamic>[
        <String, dynamic>{"score": 1},
      ]);
      expect(rows, isEmpty);
    });

    test("accepts plain strings and numbers", () {
      final List<ExamSolutionStepRow> rows = solutionListToTableRows(<dynamic>[
        "  text  ",
        3,
      ]);
      expect(rows.map((ExamSolutionStepRow r) => r.step).toList(), <String>["text", "3"]);
    });
  });

  group("parseMarkdownTableToStepRows", () {
    test("parses simple pipe table", () {
      const String md = """
| Pas | Punctaj |
| --- | --- |
| Demonstrație | 1p |
""";
      final List<ExamSolutionStepRow> rows = parseMarkdownTableToStepRows(md);
      expect(rows.length, 1);
      expect(rows.first.step, "Demonstrație");
      expect(rows.first.score, closeTo(1, 0.001));
    });
  });

  group("tryParseBaremChunkAsJsonRows", () {
    test("parses JSON list of steps", () {
      const String chunk = '[{"step":"x","score":2}]';
      final List<ExamSolutionStepRow>? rows = tryParseBaremChunkAsJsonRows(chunk);
      expect(rows, isNotNull);
      expect(rows!.single.step, "x");
      expect(rows.single.score, 2);
    });

    test("returns null for non-array", () {
      expect(tryParseBaremChunkAsJsonRows('{"a":1}'), isNull);
    });
  });

  group("computeExamMarkingDisplay extended shapes", () {
    test("map with item_solutions list yields table rows", () {
      final display = computeExamMarkingDisplay(
        solutionJson: <String, dynamic>{
          "item_solutions": <dynamic>[
            <String, dynamic>{"step": "Item A", "score": 2},
          ],
        },
        scoringScaleChunks: <String>[],
      );
      expect(display.tableRows.length, 1);
      expect(display.tableRows.first.step, "Item A");
    });

    test("map with numeric string keys becomes ordered list", () {
      final display = computeExamMarkingDisplay(
        solutionJson: <String, dynamic>{
          "2": <dynamic>[
            <String, dynamic>{"step": "second", "score": 1},
          ],
          "1": <dynamic>[
            <String, dynamic>{"step": "first", "score": 1},
          ],
        },
        scoringScaleChunks: <String>[],
      );
      expect(display.tableRows.map((ExamSolutionStepRow r) => r.step).toList(),
          <String>["first", "second"]);
    });

    test("unwrap drills through solution_steps to list", () {
      final display = computeExamMarkingDisplay(
        solutionJson: <String, dynamic>{
          "solution_steps": <dynamic>[
            <String, dynamic>{"step": "Deep", "punctaj": 1},
          ],
        },
        scoringScaleChunks: <String>[],
      );
      expect(display.tableRows.single.step, "Deep");
    });

    test("JSON string solution decodes to rows", () {
      final display = computeExamMarkingDisplay(
        solutionJson: '[{"step":"JS","score":3}]',
        scoringScaleChunks: <String>[],
      );
      expect(display.tableRows.single.step, "JS");
    });

    test("invalid JSON string falls back to plain markdown", () {
      final display = computeExamMarkingDisplay(
        solutionJson: "[not json",
        scoringScaleChunks: <String>[],
      );
      expect(display.markdown, "[not json");
    });

    test("solutionListToTableRows handles nested list via formatFieldForDisplay", () {
      final List<ExamSolutionStepRow> rows = solutionListToTableRows(<dynamic>[
        <String, dynamic>{"step": <dynamic>["line1", "line2"], "score": 1},
      ]);
      expect(rows.single.step, "line1\nline2");
    });

    test("rowsFromScoringScaleChunks aggregates chunks", () {
      final display = computeExamMarkingDisplay(
        solutionJson: null,
        scoringScaleChunks: <String>[
          '[{"step":"From chunk","score":1}]',
        ],
      );
      expect(display.tableRows.single.step, "From chunk");
    });

    test("map with single unknown list key drills into list", () {
      final display = computeExamMarkingDisplay(
        solutionJson: <String, dynamic>{
          "custom_list": <dynamic>[
            <String, dynamic>{"step": "C", "score": 1},
          ],
        },
        scoringScaleChunks: <String>[],
      );
      expect(display.tableRows.single.step, "C");
    });

    test("empty solution map yields empty display", () {
      final display = computeExamMarkingDisplay(
        solutionJson: <String, dynamic>{},
        scoringScaleChunks: <String>[],
      );
      expect(display.tableRows, isEmpty);
      expect(display.markdown, isNull);
    });

    test("markdown table skips punctaj header row", () {
      const String md = """
| Pas | Punctaj |
| --- | --- |
| Row | 2p |
""";
      final List<ExamSolutionStepRow> rows = parseMarkdownTableToStepRows(md);
      expect(rows.length, 1);
      expect(rows.first.step, "Row");
    });

    test("prose-only scoring chunks become markdown display", () {
      final display = computeExamMarkingDisplay(
        solutionJson: null,
        scoringScaleChunks: <String>["Barem **fara** tabel"],
      );
      expect(display.markdown, contains("Barem"));
      expect(display.tableRows, isEmpty);
    });
  });

  group("computeExamMarkingDisplay", () {
    test("prefers list solution as table", () {
      final display = computeExamMarkingDisplay(
        solutionJson: <dynamic>[
          <String, dynamic>{"step": "S", "score": 1},
        ],
        scoringScaleChunks: <String>[],
      );
      expect(display.tableRows, isNotEmpty);
      expect(display.markdown, isNull);
    });

    test("uses string solution as markdown and appends scales", () {
      final display = computeExamMarkingDisplay(
        solutionJson: "Intro text",
        scoringScaleChunks: <String>["Extra"],
      );
      expect(display.tableRows, isEmpty);
      expect(display.markdown, contains("Intro"));
      expect(display.markdown, contains("Extra"));
    });

    test("uses scoring chunks when solution empty", () {
      final display = computeExamMarkingDisplay(
        solutionJson: null,
        scoringScaleChunks: <String>["| Pas | Punctaj |\n| --- | --- |\n| A | 1 |"],
      );
      expect(display.tableRows, isNotEmpty);
    });
  });
}
