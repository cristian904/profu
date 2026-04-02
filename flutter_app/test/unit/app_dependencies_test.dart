import "package:flutter_dotenv/flutter_dotenv.dart";
import "package:flutter_test/flutter_test.dart";
import "package:profu_app/core/di/app_dependencies.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:supabase_flutter/supabase_flutter.dart";

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues(<String, Object>{});
    dotenv.testLoad(mergeWith: <String, String>{"API_BASE_URL": "http://deps.test"});
    await Supabase.initialize(
      url: "https://test.supabase.co",
      anonKey: "test-anon-key",
    );
  });

  test("fromEnvironment wires Supabase client and conversation repository", () {
    final AppDependencies deps = AppDependencies.fromEnvironment();
    expect(deps.supabase, same(Supabase.instance.client));
    expect(deps.apiBaseUrl, "http://deps.test");
    deps.httpClient.close();
  });
}
