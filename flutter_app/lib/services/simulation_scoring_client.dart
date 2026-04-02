import "dart:convert";

import "package:flutter/foundation.dart";
import "package:http/http.dart" as http;

import "../models/simulation_scoring_payload.dart";

/// HTTP client for `POST /simulari/scoring` (inject [client] for tests).
class SimulationScoringClient {
  /// Creates a client with explicit [apiBaseUrl] and [client].
  SimulationScoringClient({
    required this.client,
    required this.apiBaseUrl,
  });

  final http.Client client;
  final String apiBaseUrl;

  /// Submits per-problem scores; returns the summed total from the server.
  Future<double> submitPerProblemScores({
    required String accessToken,
    required int simulationId,
    required List<SimulationProblemScorePayload> problems,
  }) async {
    if (accessToken.isEmpty) {
      throw Exception("Missing auth session. Please sign in again.");
    }
    if (problems.isEmpty) {
      throw Exception("No problem scores to submit.");
    }

    final Uri endpoint = Uri.parse("$apiBaseUrl/simulari/scoring");
    if (kDebugMode) {
      debugPrint(
        "[SimulationScoringClient] POST scoring simulation_id=$simulationId "
        "problems_count=${problems.length}",
      );
    }

    try {
      final http.Response response = await client.post(
        endpoint,
        headers: <String, String>{
          "Content-Type": "application/json",
          "Authorization": "Bearer $accessToken",
        },
        body: jsonEncode(<String, dynamic>{
          "simulation_id": simulationId,
          "problems": problems.map((SimulationProblemScorePayload e) => e.toJson()).toList(),
        }),
      );

      if (kDebugMode) {
        debugPrint("[SimulationScoringClient] Response status: ${response.statusCode}");
        debugPrint("[SimulationScoringClient] Response body: ${response.body}");
      }

      if (response.statusCode != 200) {
        String message = "Nu s-a putut salva scorul.";
        try {
          final dynamic decoded = jsonDecode(response.body);
          if (decoded is Map<String, dynamic>) {
            final dynamic detail = decoded["detail"];
            if (detail is String && detail.isNotEmpty) {
              message = detail;
            } else if (detail is List<dynamic>) {
              message = detail.map((dynamic e) => e.toString()).join("; ");
            }
          }
        } catch (_) {
          // Keep default message.
        }
        throw Exception(message);
      }

      final Map<String, dynamic> payload = jsonDecode(response.body) as Map<String, dynamic>;
      final dynamic total = payload["total_score"];
      if (total is num) {
        return total.toDouble();
      }
      throw Exception("Invalid scoring response from server.");
    } catch (e, st) {
      if (kDebugMode) {
        debugPrint("[SimulationScoringClient] submitPerProblemScores error: $e\n$st");
      }
      rethrow;
    }
  }
}
