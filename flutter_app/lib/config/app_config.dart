import 'package:flutter_dotenv/flutter_dotenv.dart';

/// App configuration loaded from .env (same file as ai_backend: repo root .env
/// is copied to flutter_app/.env when you run `poe ui` from repo root).
class AppConfig {
  AppConfig._();

  /// Base URL of the FastAPI backend (set API_BASE_URL in root .env; poe ai uses port 8080).
  static String get apiBaseUrl =>
      dotenv.env['API_BASE_URL'] ?? 'http://localhost:8080';

  /// Supabase project URL (local: http://127.0.0.1:54321, or hosted project URL).
  static String get supabaseUrl =>
      dotenv.env['SUPABASE_URL'] ?? 'http://127.0.0.1:54321';

  /// Supabase anon (public) key for client-side auth.
  static String get supabaseAnonKey =>
      dotenv.env['SUPABASE_ANON_KEY'] ?? '';
}
