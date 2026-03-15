import "package:flutter/foundation.dart";
import "package:flutter_dotenv/flutter_dotenv.dart";

/// App configuration loaded from .env (same file as ai_backend: repo root .env
/// is copied to flutter_app/.env when you run `poe ui` from repo root).
/// On web, dotenv may not load (asset 404); fallbacks ensure local Supabase still works.
class AppConfig {
  AppConfig._();

  static const String _defaultSupabaseUrl = "http://127.0.0.1:54321";

  /// Well-known anon key for local Supabase (npx supabase start). Used only when
  /// .env did not load and URL is local, so Supabase.initialize does not get an empty key.
  static const String _localSupabaseAnonKey =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_Iw";

  /// Base URL of the FastAPI backend (set API_BASE_URL in root .env; poe ai uses port 8080).
  static String get apiBaseUrl =>
      dotenv.env["API_BASE_URL"] ?? "http://localhost:8080";

  /// Supabase project URL (local: http://127.0.0.1:54321, or hosted project URL).
  static String get supabaseUrl =>
      dotenv.env["SUPABASE_URL"] ?? _defaultSupabaseUrl;

  /// Supabase anon (public) key for client-side auth.
  /// When on web and .env did not load, uses local Supabase anon key if URL is local
  /// so Supabase.initialize does not receive an empty key (NotInitializedError).
  static String get supabaseAnonKey {
    final fromEnv = dotenv.env["SUPABASE_ANON_KEY"] ?? "";
    if (fromEnv.isNotEmpty) return fromEnv;
    final url = supabaseUrl;
    if (url == _defaultSupabaseUrl) return _localSupabaseAnonKey;
    if (kDebugMode) {
      debugPrint("[AppConfig] SUPABASE_ANON_KEY empty and URL is not local; auth may fail.");
    }
    return "";
  }
}
