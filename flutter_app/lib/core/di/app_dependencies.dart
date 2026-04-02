import "package:http/http.dart" as http;
import "package:supabase_flutter/supabase_flutter.dart";

import "../config/app_config.dart";
import "../../services/conversation_repository.dart";
import "../../services/conversation_repository_api.dart";

/// Injectable application services for production and tests.
class AppDependencies {
  /// Creates dependencies used by the UI layer.
  AppDependencies({
    required this.supabase,
    required this.httpClient,
    required this.apiBaseUrl,
    ConversationRepositoryApi? conversationRepository,
  }) : conversationRepository =
            conversationRepository ?? ConversationRepository(client: supabase);

  /// Authenticated Supabase client (same instance as [Supabase.instance.client] after init).
  final SupabaseClient supabase;

  /// Shared HTTP client for backend calls (owns lifecycle unless replaced in tests).
  final http.Client httpClient;

  /// FastAPI base URL (no trailing slash required).
  final String apiBaseUrl;

  /// Conversations / messages persistence.
  final ConversationRepositoryApi conversationRepository;

  /// Builds defaults after [Supabase.initialize] and dotenv load.
  factory AppDependencies.fromEnvironment() {
    return AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: http.Client(),
      apiBaseUrl: AppConfig.apiBaseUrl,
    );
  }
}
