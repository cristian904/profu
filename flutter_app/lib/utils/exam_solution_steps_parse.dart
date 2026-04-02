import "dart:convert";

import "package:flutter/foundation.dart";

import "../models/exam_marking_display.dart";
import "../models/exam_solution_step_row.dart";

/// Parses a numeric score from JSON or strings like "1p", "0,5", "2".
double? _parseScoreValue(dynamic raw) {
  if (raw == null) {
    return null;
  }
  if (raw is num) {
    return raw.toDouble();
  }
  if (raw is String) {
    final String cleaned = raw
        .trim()
        .replaceAll(RegExp(r"p$", caseSensitive: false), "")
        .replaceAll(",", ".")
        .replaceAll(RegExp(r"[^\d.-]"), "");
    if (cleaned.isEmpty) {
      return null;
    }
    return double.tryParse(cleaned);
  }
  return null;
}

/// Formats a JSON value for display in the **Pas** column (never raw `Map.toString()` / JSON dump).
String? _formatFieldForDisplay(dynamic v) {
  if (v == null) {
    return null;
  }
  if (v is String) {
    final String t = v.trim();
    return t.isEmpty ? null : t;
  }
  if (v is num || v is bool) {
    return v.toString();
  }
  if (v is List<dynamic>) {
    final List<String> parts = <String>[];
    for (final dynamic x in v) {
      final String? s = _formatFieldForDisplay(x);
      if (s != null) {
        parts.add(s);
      }
    }
    if (parts.isEmpty) {
      return null;
    }
    return parts.join("\n");
  }
  if (v is Map) {
    final Map<String, dynamic> map = Map<String, dynamic>.from(v);
    for (final String k in <String>[
      "step",
      "solution",
      "solution_steps",
      "text",
      "description",
      "enunt",
      "continut",
      "value",
    ]) {
      if (!map.containsKey(k)) {
        continue;
      }
      final String? s = _formatFieldForDisplay(map[k]);
      if (s != null) {
        return s;
      }
    }
    return null;
  }
  return null;
}

/// Reads the **Pas** text from a barem / item object (matches merged JSON: [solution], [solution_steps], [step], …).
String? _stepDisplayFromMap(Map<String, dynamic> m) {
  final dynamic key = m["step"] ??
      m["solution"] ??
      m["solution_steps"] ??
      m["rezolvare"] ??
      m["description"] ??
      m["text"] ??
      m["cerinta"] ??
      m["cerință"];
  if (key == null) {
    return null;
  }
  return _formatFieldForDisplay(key);
}

/// Drills common wrappers until a list/string leaf (includes **item_solutions** from load_merged_to_db s2/s3).
dynamic unwrapSolutionPayload(dynamic raw) {
  if (raw == null) {
    return null;
  }
  dynamic current = raw;
  while (current is Map) {
    final Map<String, dynamic> m = Map<String, dynamic>.from(current);
    final dynamic next = m["solution_steps"] ??
        m["item_solutions"] ??
        m["steps"] ??
        m["barem"];
    if (next == null) {
      break;
    }
    current = next;
  }
  return current;
}

/// Handles a [Map] left after [unwrapSolutionPayload] (nested `{ item_solutions: [...] }`, single-list maps, etc.).
_ParsedSolutionSide parseSolutionFromMap(Map<String, dynamic> m) {
  const List<String> listKeys = <String>[
    "item_solutions",
    "solution_steps",
    "steps",
    "barem",
    "entries",
    "rows",
    "solutions",
  ];
  for (final String k in listKeys) {
    final dynamic v = m[k];
    if (v != null) {
      return parseSolutionSide(v);
    }
  }
  final List<MapEntry<String, dynamic>> listEntries =
      m.entries.where((MapEntry<String, dynamic> e) => e.value is List).toList();
  if (listEntries.length == 1) {
    return parseSolutionSide(listEntries.first.value);
  }
  if (m.isNotEmpty &&
      m.keys.every((Object k) => int.tryParse(k.toString()) != null)) {
    final List<int> sortedKeys = m.keys.map((Object k) => int.parse(k.toString())).toList()
      ..sort();
    final List<dynamic> asList = <dynamic>[
      for (final int ik in sortedKeys) m[ik.toString()],
    ];
    return parseSolutionSide(asList);
  }
  if (kDebugMode) {
    debugPrint(
      "[exam_solution_steps_parse] solution map has no list field; keys=${m.keys.toList()}",
    );
  }
  return const _ParsedSolutionSide();
}

/// One table row per list element: maps use **step** and **score** / **punctaj** values only.
List<ExamSolutionStepRow> solutionListToTableRows(List<dynamic> list) {
  final List<ExamSolutionStepRow> out = <ExamSolutionStepRow>[];
  for (final dynamic e in list) {
    if (e == null) {
      continue;
    }
    if (e is Map) {
      final Map<String, dynamic> m = Map<String, dynamic>.from(e);
      final String? stepText = _stepDisplayFromMap(m);
      if (stepText == null || stepText.isEmpty) {
        if (kDebugMode) {
          debugPrint(
            "[exam_solution_steps_parse] skipping list item without displayable step field",
          );
        }
        continue;
      }
      final double? sc = _parseScoreValue(
        m["score"] ?? m["punctaj"] ?? m["puncte"] ?? m["points"] ?? m["pct"],
      );
      out.add(ExamSolutionStepRow(step: stepText, score: sc));
      continue;
    }
    if (e is String) {
      final String t = e.trim();
      if (t.isNotEmpty) {
        out.add(ExamSolutionStepRow(step: t, score: null));
      }
      continue;
    }
    if (e is num || e is bool) {
      out.add(ExamSolutionStepRow(step: e.toString(), score: null));
      continue;
    }
    final String? nested = _formatFieldForDisplay(e);
    if (nested != null && nested.isNotEmpty) {
      out.add(ExamSolutionStepRow(step: nested, score: null));
    }
  }
  return out;
}

/// Parses [exam_problems.solution] into either table rows or plain text (string → no table).
class _ParsedSolutionSide {
  /// Creates the solution part of marking display.
  const _ParsedSolutionSide({
    this.tableRows = const <ExamSolutionStepRow>[],
    this.plainText,
  });

  final List<ExamSolutionStepRow> tableRows;
  final String? plainText;
}

/// Classifies `solution` JSONB: **list** → table rows; **string** → plain markdown only.
_ParsedSolutionSide parseSolutionSide(dynamic solutionJson) {
  final dynamic u = unwrapSolutionPayload(solutionJson);
  if (u == null) {
    return const _ParsedSolutionSide();
  }
  if (u is String) {
    final String t = u.trim();
    if (t.isEmpty) {
      return const _ParsedSolutionSide();
    }
    if (t.startsWith("[") || t.startsWith("{")) {
      try {
        final dynamic decoded = jsonDecode(t);
        return parseSolutionSide(decoded);
      } catch (e) {
        if (kDebugMode) {
          debugPrint("[exam_solution_steps_parse] solution string not JSON: $e");
        }
        return _ParsedSolutionSide(plainText: t);
      }
    }
    return _ParsedSolutionSide(plainText: t);
  }
  if (u is List) {
    return _ParsedSolutionSide(
      tableRows: solutionListToTableRows(List<dynamic>.from(u)),
    );
  }
  if (u is Map) {
    return parseSolutionFromMap(Map<String, dynamic>.from(u));
  }
  if (kDebugMode) {
    debugPrint("[exam_solution_steps_parse] unexpected solution shape: ${u.runtimeType}");
  }
  return const _ParsedSolutionSide();
}

/// True if [line] looks like a markdown table separator row.
bool _isMarkdownTableSeparatorLine(String line) {
  final String t = line.replaceAll(" ", "");
  return t.contains("---") && t.contains("|");
}

/// True if this row is treated as a header (skip as data).
bool _looksLikeMarkdownHeader(List<String> cells) {
  if (cells.isEmpty) {
    return false;
  }
  final String joined = cells.join(" ").toLowerCase();
  return joined.contains("punctaj") ||
      joined.contains("punct") ||
      joined.contains("scor") ||
      (joined.contains("pas") && joined.contains("observa"));
}

/// Splits a markdown table line into trimmed cell strings (excluding outer empty parts).
List<String> _markdownTableCells(String line) {
  final List<String> parts = line.split("|");
  if (parts.isEmpty) {
    return <String>[];
  }
  final List<String> cells = <String>[];
  for (int i = 0; i < parts.length; i++) {
    final String c = parts[i].trim();
    if (c.isEmpty && (i == 0 || i == parts.length - 1)) {
      continue;
    }
    cells.add(c);
  }
  return cells;
}

/// Extracts step/score rows from a markdown pipe table in a barem chunk.
List<ExamSolutionStepRow> parseMarkdownTableToStepRows(String markdown) {
  if (markdown.trim().isEmpty) {
    return <ExamSolutionStepRow>[];
  }

  final List<ExamSolutionStepRow> out = <ExamSolutionStepRow>[];
  final List<String> lines = markdown.split("\n");
  bool skippedHeader = false;

  for (final String rawLine in lines) {
    final String line = rawLine.trim();
    if (!line.contains("|")) {
      continue;
    }
    if (_isMarkdownTableSeparatorLine(line)) {
      continue;
    }
    final List<String> cells = _markdownTableCells(line);
    if (cells.length < 2) {
      continue;
    }
    if (!skippedHeader && _looksLikeMarkdownHeader(cells)) {
      skippedHeader = true;
      continue;
    }
    skippedHeader = true;

    final String stepText = cells.first;
    if (stepText.isEmpty) {
      continue;
    }
    final String scoreCell = cells.length > 1 ? cells.last : "";
    final double? sc = _parseScoreValue(scoreCell);
    out.add(ExamSolutionStepRow(step: stepText, score: sc));
  }
  return out;
}

/// If [chunk] is a JSON array of `{step, score}`, returns rows; otherwise null.
List<ExamSolutionStepRow>? tryParseBaremChunkAsJsonRows(String chunk) {
  final String t = chunk.trim();
  if (!t.startsWith("[")) {
    return null;
  }
  try {
    final dynamic d = jsonDecode(t);
    if (d is! List<dynamic>) {
      return null;
    }
    final List<ExamSolutionStepRow> rows = solutionListToTableRows(d);
    return rows.isEmpty ? null : rows;
  } catch (e) {
    if (kDebugMode) {
      debugPrint("[exam_solution_steps_parse] chunk is not JSON step list: $e");
    }
    return null;
  }
}

/// Builds table rows from `scoring_scales` text chunks (JSON step list or markdown table).
List<ExamSolutionStepRow> rowsFromScoringScaleChunks(List<String> scoringScaleChunks) {
  final List<ExamSolutionStepRow> out = <ExamSolutionStepRow>[];
  for (final String chunk in scoringScaleChunks) {
    final List<ExamSolutionStepRow>? jsonRows = tryParseBaremChunkAsJsonRows(chunk);
    if (jsonRows != null) {
      out.addAll(jsonRows);
      continue;
    }
    out.addAll(parseMarkdownTableToStepRows(chunk));
  }
  return out;
}

/// Appends non-empty barem chunks to [buffer] (plain markdown).
void appendScoringMarkdownChunks(StringBuffer buffer, List<String> scoringScaleChunks) {
  final String joined =
      scoringScaleChunks.where((String c) => c.trim().isNotEmpty).join("\n\n");
  if (joined.isEmpty) {
    return;
  }
  if (buffer.isNotEmpty) {
    buffer.writeln();
    buffer.writeln();
  }
  buffer.write(joined);
}

/// Computes table vs prose: **string `solution_steps` → markdown only**; **list → Pas/Punctaj table**.
ExamMarkingDisplay computeExamMarkingDisplay({
  required dynamic solutionJson,
  required List<String> scoringScaleChunks,
}) {
  final _ParsedSolutionSide side = parseSolutionSide(solutionJson);

  if (side.tableRows.isNotEmpty) {
    return ExamMarkingDisplay(
      tableRows: side.tableRows,
      markdown: null,
    );
  }

  if (side.plainText != null && side.plainText!.trim().isNotEmpty) {
    final StringBuffer buf = StringBuffer(side.plainText!.trim());
    appendScoringMarkdownChunks(buf, scoringScaleChunks);
    return ExamMarkingDisplay(
      tableRows: <ExamSolutionStepRow>[],
      markdown: buf.toString().trim(),
    );
  }

  final List<ExamSolutionStepRow> scaleRows = rowsFromScoringScaleChunks(scoringScaleChunks);
  if (scaleRows.isNotEmpty) {
    return ExamMarkingDisplay(tableRows: scaleRows, markdown: null);
  }

  final String onlyChunks =
      scoringScaleChunks.where((String c) => c.trim().isNotEmpty).join("\n\n");
  if (onlyChunks.isNotEmpty) {
    return ExamMarkingDisplay(
      tableRows: <ExamSolutionStepRow>[],
      markdown: onlyChunks,
    );
  }

  return const ExamMarkingDisplay(tableRows: <ExamSolutionStepRow>[], markdown: null);
}
