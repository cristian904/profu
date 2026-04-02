import "dart:convert";

import "package:flutter_dotenv/flutter_dotenv.dart";
import "package:flutter_test/flutter_test.dart";
import "package:http/http.dart" as http;
import "package:http/testing.dart";
import "package:profu_app/services/simulation_scoring_api.dart";

void main() {
  test("submitSimulationPerProblemScores delegates with injectable client", () async {
    dotenv.testLoad(mergeWith: <String, String>{"API_BASE_URL": "http://api.wrap"});

    final http.Client client = MockClient((http.BaseRequest request) async {
      return http.Response(jsonEncode(<String, dynamic>{"total_score": 10}), 200);
    });

    final double total = await submitSimulationPerProblemScores(
      accessToken: "t",
      simulationId: 5,
      problems: const <SimulationProblemScorePayload>[
        SimulationProblemScorePayload(
          subjectNumber: 1,
          problemNumber: 1,
          studentScore: 5,
        ),
      ],
      httpClient: client,
    );
    expect(total, 10);
  });

  test("submitSimulationPerProblemScores throws when total_score missing on 200", () async {
    dotenv.testLoad(mergeWith: <String, String>{"API_BASE_URL": "http://api.wrap"});
    final http.Client client = MockClient(
      (_) async => http.Response("{}", 200),
    );
    await expectLater(
      submitSimulationPerProblemScores(
        accessToken: "t",
        simulationId: 1,
        problems: const <SimulationProblemScorePayload>[
          SimulationProblemScorePayload(
            subjectNumber: 1,
            problemNumber: 1,
            studentScore: 1,
          ),
        ],
        httpClient: client,
      ),
      throwsException,
    );
  });
}
