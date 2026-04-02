import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:http/http.dart" as http;
import "package:http/testing.dart";
import "package:profu_app/models/simulation_scoring_payload.dart";
import "package:profu_app/services/simulation_scoring_client.dart";

void main() {
  group("SimulationScoringClient", () {
    test("submitPerProblemScores returns total on 200", () async {
      final MockClient client = MockClient((http.BaseRequest request) async {
        expect(request.url.toString(), "http://api.test/simulari/scoring");
        final Map<String, dynamic> body =
            jsonDecode((request as http.Request).body) as Map<String, dynamic>;
        expect(body["simulation_id"], 10);
        expect(body["problems"], isA<List<dynamic>>());
        return http.Response(jsonEncode(<String, dynamic>{"total_score": 42.5}), 200);
      });

      final SimulationScoringClient api = SimulationScoringClient(
        client: client,
        apiBaseUrl: "http://api.test",
      );

      final double total = await api.submitPerProblemScores(
        accessToken: "tok",
        simulationId: 10,
        problems: const <SimulationProblemScorePayload>[
          SimulationProblemScorePayload(
            subjectNumber: 1,
            problemNumber: 1,
            studentScore: 5,
          ),
        ],
      );
      expect(total, 42.5);
    });

    test("throws when accessToken empty", () async {
      final SimulationScoringClient api = SimulationScoringClient(
        client: MockClient((_) async => http.Response("{}", 200)),
        apiBaseUrl: "http://api.test",
      );
      expect(
        () => api.submitPerProblemScores(
          accessToken: "",
          simulationId: 1,
          problems: const <SimulationProblemScorePayload>[
            SimulationProblemScorePayload(
              subjectNumber: 1,
              problemNumber: 1,
              studentScore: 1,
            ),
          ],
        ),
        throwsException,
      );
    });

    test("throws when problems empty", () async {
      final SimulationScoringClient api = SimulationScoringClient(
        client: MockClient((_) async => http.Response("{}", 200)),
        apiBaseUrl: "http://api.test",
      );
      expect(
        () => api.submitPerProblemScores(
          accessToken: "t",
          simulationId: 1,
          problems: const <SimulationProblemScorePayload>[],
        ),
        throwsException,
      );
    });

    test("non-200 uses detail string when present", () async {
      final MockClient client = MockClient(
        (_) async => http.Response(
          jsonEncode(<String, dynamic>{"detail": "custom error"}),
          422,
        ),
      );
      final SimulationScoringClient api = SimulationScoringClient(
        client: client,
        apiBaseUrl: "http://api.test",
      );
      expect(
        () => api.submitPerProblemScores(
          accessToken: "t",
          simulationId: 1,
          problems: const <SimulationProblemScorePayload>[
            SimulationProblemScorePayload(
              subjectNumber: 1,
              problemNumber: 1,
              studentScore: 1,
            ),
          ],
        ),
        throwsA(isA<Exception>().having(
          (Exception e) => e.toString(),
          "message",
          contains("custom error"),
        )),
      );
    });
  });

  group("SimulationProblemScorePayload", () {
    test("toJson shape", () {
      const SimulationProblemScorePayload p = SimulationProblemScorePayload(
        subjectNumber: 2,
        problemNumber: 3,
        studentScore: 7.5,
      );
      expect(p.toJson(), <String, dynamic>{
        "subject_number": 2,
        "problem_number": 3,
        "student_score": 7.5,
      });
    });
  });
}
