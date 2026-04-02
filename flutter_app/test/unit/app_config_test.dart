import "package:flutter_dotenv/flutter_dotenv.dart";
import "package:flutter_test/flutter_test.dart";
import "package:profu_app/core/config/app_config.dart";

void main() {
  group("AppConfig", () {
    tearDown(() {
      dotenv.clean();
      dotenv.testLoad(fileInput: "");
    });

    test("apiBaseUrl uses mergeWith value when set", () {
      dotenv.testLoad(mergeWith: <String, String>{"API_BASE_URL": "http://custom:9999"});
      expect(AppConfig.apiBaseUrl, "http://custom:9999");
    });

    test("apiBaseUrl falls back to localhost when missing", () {
      dotenv.testLoad(mergeWith: <String, String>{});
      expect(AppConfig.apiBaseUrl, "http://localhost:8080");
    });

    test("supabaseUrl falls back to local default", () {
      dotenv.testLoad(mergeWith: <String, String>{});
      expect(AppConfig.supabaseUrl, "http://127.0.0.1:54321");
    });

    test("supabaseAnonKey uses env when non-empty", () {
      dotenv.testLoad(mergeWith: <String, String>{
        "SUPABASE_ANON_KEY": "my-key",
        "SUPABASE_URL": "https://xyz.supabase.co",
      });
      expect(AppConfig.supabaseAnonKey, "my-key");
    });

    test("supabaseAnonKey uses local well-known key when URL is local and key empty", () {
      dotenv.testLoad(mergeWith: <String, String>{
        "SUPABASE_URL": "http://127.0.0.1:54321",
        "SUPABASE_ANON_KEY": "",
      });
      expect(AppConfig.supabaseAnonKey, isNotEmpty);
    });
  });
}
