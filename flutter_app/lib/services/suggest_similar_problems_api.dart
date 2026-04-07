import "dart:convert";

import "package:flutter/foundation.dart";
import "package:http/http.dart" as http;
import "package:supabase_flutter/supabase_flutter.dart";

import "../core/config/app_config.dart";

/// Typed result from [suggestSimilarProblems].
class SuggestSimilarProblemsResult {
  /// Creates a result from the RAG API.
  SuggestSimilarProblemsResult({
    required this.message,
    required this.statements,
  });

  /// Assistant-style Romanian message listing similar problems.
  final String message;

  /// Up to five statement strings for "Problema 1" … buttons.
  final List<String> statements;
}

/// Parses a 200 JSON body from `/rag/suggest-problem`. Returns null if JSON is invalid.
SuggestSimilarProblemsResult? parseSuccessResponseBody(String body) {
  try {
    final Object? decoded = json.decode(body);
    if (decoded is! Map<String, dynamic>) {
      return null;
    }
    return parseSuccessResponseMap(decoded);
  } catch (_) {
    return null;
  }
}

/// Parses the success payload map (used by tests and [parseSuccessResponseBody]).
SuggestSimilarProblemsResult parseSuccessResponseMap(Map<String, dynamic> data) {
  final String message =
      data["message"] as String? ?? "Nu am găsit probleme similare.";
  final List<dynamic> problemsList = data["problems"] as List<dynamic>? ?? <dynamic>[];
  final List<String> statements = problemsList
      .map((dynamic e) {
        if (e is Map<String, dynamic>) {
          return e["statement"] as String? ?? "";
        }
        return "";
      })
      .toList();
  return SuggestSimilarProblemsResult(message: message, statements: statements);
}

/// Calls `POST /rag/suggest-problem` (vector similarity over indexed exam statements).
class SuggestSimilarProblemsApi {
  SuggestSimilarProblemsApi._();

  static final String _baseUrl = "${AppConfig.apiBaseUrl}/rag/suggest-problem";

  /// Returns null on HTTP/network failure (caller shows SnackBar).
  static Future<SuggestSimilarProblemsResult?> suggest({
    required String problemText,
  }) async {
    final String trimmed = problemText.trim();
    if (trimmed.isEmpty) {
      debugPrint("[SuggestSimilarProblemsApi] Skipped: empty problem_text");
      return null;
    }

    try {
      debugPrint("[SuggestSimilarProblemsApi] POST suggest-problem (length=${trimmed.length})");
      final http.Request request = http.Request("POST", Uri.parse(_baseUrl));
      request.headers["Content-Type"] = "application/json";
      final String? token = Supabase.instance.client.auth.currentSession?.accessToken;
      if (token != null) {
        request.headers["Authorization"] = "Bearer $token";
      }
      request.body = json.encode(<String, dynamic>{"problem_text": trimmed});

      final http.StreamedResponse response = await request.send();
      final String body = await response.stream.transform(utf8.decoder).join();

      if (response.statusCode != 200) {
        debugPrint(
          "[SuggestSimilarProblemsApi] Error status=${response.statusCode} body=${body.length > 200 ? "${body.substring(0, 200)}..." : body}",
        );
        return null;
      }

      final SuggestSimilarProblemsResult? parsed = parseSuccessResponseBody(body);
      if (parsed == null) {
        debugPrint("[SuggestSimilarProblemsApi] Failed to parse success body");
        return null;
      }

      debugPrint(
        "[SuggestSimilarProblemsApi] Success: ${parsed.statements.length} problem statement(s)",
      );
      return parsed;
    } catch (e, st) {
      debugPrint("[SuggestSimilarProblemsApi] Exception: $e");
      debugPrint("[SuggestSimilarProblemsApi] Stack: $st");
      return null;
    }
  }
}
