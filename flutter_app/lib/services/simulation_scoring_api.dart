import "package:http/http.dart" as http;

import "../core/config/app_config.dart";
import "../models/simulation_scoring_payload.dart";
import "simulation_scoring_client.dart";

export "../models/simulation_scoring_payload.dart";

/// Submits per-problem scores; server returns the summed total.
/// Prefer [SimulationScoringClient] in new code for testability.
Future<double> submitSimulationPerProblemScores({
  required String accessToken,
  required int simulationId,
  required List<SimulationProblemScorePayload> problems,
  http.Client? httpClient,
}) async {
  final http.Client client = httpClient ?? http.Client();
  final bool ownsClient = httpClient == null;
  try {
    return await SimulationScoringClient(
      client: client,
      apiBaseUrl: AppConfig.apiBaseUrl,
    ).submitPerProblemScores(
      accessToken: accessToken,
      simulationId: simulationId,
      problems: problems,
    );
  } finally {
    if (ownsClient) {
      client.close();
    }
  }
}
