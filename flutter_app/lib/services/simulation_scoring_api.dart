import "dart:convert";

import "package:flutter/foundation.dart";
import "package:http/http.dart" as http;

import "../config/app_config.dart";

/// One row for `POST /simulari/scoring` [problems] array.
class SimulationProblemScorePayload {
  /// Creates a per-problem score line.
  const SimulationProblemScorePayload({
    required this.subjectNumber,
    required this.problemNumber,
    required this.studentScore,
  });

  final int subjectNumber;
  final int problemNumber;
  final double studentScore;

  /// JSON object for the API body.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      "subject_number": subjectNumber,
      "problem_number": problemNumber,
      "student_score": studentScore,
    };
  }
}

/// Submits per-problem scores; server returns the summed total.
Future<double> submitSimulationPerProblemScores({
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

  final Uri endpoint = Uri.parse("${AppConfig.apiBaseUrl}/simulari/scoring");
  if (kDebugMode) {
    debugPrint(
      "[SimulationScoringApi] POST scoring simulation_id=$simulationId "
      "problems_count=${problems.length}",
    );
  }

  try {
    final http.Response response = await http.post(
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
      debugPrint("[SimulationScoringApi] Response status: ${response.statusCode}");
      debugPrint("[SimulationScoringApi] Response body: ${response.body}");
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
      debugPrint("[SimulationScoringApi] submitSimulationPerProblemScores error: $e\n$st");
    }
    rethrow;
  }
}
