import "package:flutter/foundation.dart";

/// Parses nested `scoring_scales` from PostgREST into ordered markdown chunks.
List<String> parseScoringScaleChunks(dynamic raw) {
  if (raw == null) {
    return <String>[];
  }
  if (raw is! List) {
    if (kDebugMode) {
      debugPrint("[simulation_problems_parse] scoring_scales is not a list: ${raw.runtimeType}");
    }
    return <String>[];
  }

  int orderKey(Map<String, dynamic> m) {
    final dynamic o = m["order_index"];
    if (o is num) {
      return o.toInt();
    }
    return 0;
  }

  final List<Map<String, dynamic>> rows = <Map<String, dynamic>>[];
  for (final dynamic e in raw) {
    if (e is Map) {
      rows.add(Map<String, dynamic>.from(e));
    }
  }
  rows.sort((Map<String, dynamic> a, Map<String, dynamic> b) {
    return orderKey(a).compareTo(orderKey(b));
  });

  final List<String> out = <String>[];
  for (final Map<String, dynamic> m in rows) {
    final String? sol = m["solution"] as String?;
    final String t = sol?.trim() ?? "";
    if (t.isNotEmpty) {
      out.add(t);
    }
  }
  return out;
}

/// Parses [exam_problems.items] JSONB into non-empty strings (Subiectul II/III sub-tasks).
List<String> parseProblemItems(dynamic raw) {
  if (raw == null) {
    return <String>[];
  }
  if (raw is! List) {
    if (kDebugMode) {
      debugPrint("[simulation_problems_parse] items is not a list, ignoring: ${raw.runtimeType}");
    }
    return <String>[];
  }
  final List<String> out = <String>[];
  for (final dynamic e in raw) {
    if (e == null) {
      continue;
    }
    final String s = e.toString().trim();
    if (s.isNotEmpty) {
      out.add(s);
    }
  }
  return out;
}
