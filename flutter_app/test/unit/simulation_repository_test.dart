import "package:flutter_test/flutter_test.dart";
import "package:profu_app/services/simulation_repository.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:supabase_flutter/supabase_flutter.dart";

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await Supabase.initialize(
      url: "https://test.supabase.co",
      anonKey: "test-anon-key",
    );
  });

  test("fetchSimulationProblemsForCurrentUser requires signed-in user", () async {
    final SimulationRepository repo = SimulationRepository(
      client: Supabase.instance.client,
    );
    expect(
      () => repo.fetchSimulationProblemsForCurrentUser(simulationId: 1),
      throwsA(isA<Exception>().having(
        (Exception e) => e.toString(),
        "message",
        contains("autentificat"),
      )),
    );
  });
}
