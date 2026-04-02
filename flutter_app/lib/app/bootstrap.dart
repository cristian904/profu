import "dart:convert";

import "package:flutter/foundation.dart";
import "package:flutter_dotenv/flutter_dotenv.dart";
import "package:http/http.dart" as http;
import "package:supabase_flutter/supabase_flutter.dart";

import "../core/config/app_config.dart";
import "../core/di/app_dependencies.dart";

/// Sends debug logs to the local Cursor agent ingestion endpoint for runtime analysis.
Future<void> agentDebugLog({
  required String hypothesisId,
  required String location,
  required String message,
  required Map<String, dynamic> data,
}) async {
  if (kDebugMode) {
    debugPrint("[AGENT_DEBUG] preparing log: $message at $location");
  }
  try {
    final Map<String, dynamic> payload = <String, dynamic>{
      "sessionId": "4d9c08",
      "runId": "initial",
      "hypothesisId": hypothesisId,
      "location": location,
      "message": message,
      "data": data,
      "timestamp": DateTime.now().millisecondsSinceEpoch,
    };
    if (kDebugMode) {
      debugPrint("[AGENT_DEBUG] sending log payload");
    }
    await http.post(
      Uri.parse("http://127.0.0.1:7745/ingest/2126c08e-9fd2-4383-8e4a-7199b0451e49"),
      headers: <String, String>{
        "Content-Type": "application/json",
        "X-Debug-Session-Id": "4d9c08",
      },
      body: jsonEncode(payload),
    );
    if (kDebugMode) {
      debugPrint("[AGENT_DEBUG] log sent successfully");
    }
  } catch (e, st) {
    debugPrint("[AGENT_DEBUG] failed to send log: $e\n$st");
  }
}

/// Loads env, initializes Supabase, and returns injectable [AppDependencies].
Future<AppDependencies> bootstrapProfuApp() async {
  try {
    if (kDebugMode) {
      debugPrint("[AGENT_DEBUG] bootstrap: starting dotenv.load (kIsWeb=$kIsWeb)");
    }
    await dotenv.load(fileName: ".env");
    if (kDebugMode) {
      debugPrint("[AGENT_DEBUG] bootstrap: dotenv.load completed");
    }
    await agentDebugLog(
      hypothesisId: kIsWeb ? "H2" : "H1",
      location: "flutter_app/lib/app/bootstrap.dart:bootstrapProfuApp:dotenv.load",
      message: "dotenv.load completed successfully",
      data: <String, dynamic>{
        "fileName": ".env",
        "platform": kIsWeb ? "web" : "non-web",
        "envCount": dotenv.env.length,
      },
    );
  } catch (e, st) {
    debugPrint("[AGENT_DEBUG] dotenv.load failed: $e");
    await agentDebugLog(
      hypothesisId: kIsWeb ? "H2" : "H1",
      location: "flutter_app/lib/app/bootstrap.dart:bootstrapProfuApp:dotenv.load",
      message: "dotenv.load threw an error",
      data: <String, dynamic>{
        "fileName": ".env",
        "platform": kIsWeb ? "web" : "non-web",
        "error": e.toString(),
        "stackTrace": st.toString(),
      },
    );
  }

  try {
    debugPrint("[AGENT_DEBUG] bootstrap: starting Supabase.initialize");
    await Supabase.initialize(
      url: AppConfig.supabaseUrl,
      anonKey: AppConfig.supabaseAnonKey,
    );
    await agentDebugLog(
      hypothesisId: "H3",
      location: "flutter_app/lib/app/bootstrap.dart:bootstrapProfuApp:Supabase.initialize",
      message: "Supabase.initialize completed successfully",
      data: <String, dynamic>{
        "supabaseUrl": AppConfig.supabaseUrl,
        "hasAnonKey": AppConfig.supabaseAnonKey.isNotEmpty,
      },
    );
  } catch (e, st) {
    debugPrint("[AGENT_DEBUG] Supabase.initialize failed: $e");
    await agentDebugLog(
      hypothesisId: "H3",
      location: "flutter_app/lib/app/bootstrap.dart:bootstrapProfuApp:Supabase.initialize",
      message: "Supabase.initialize threw an error",
      data: <String, dynamic>{
        "error": e.toString(),
        "stackTrace": st.toString(),
        "supabaseUrl": AppConfig.supabaseUrl,
        "hasAnonKey": AppConfig.supabaseAnonKey.isNotEmpty,
      },
    );
    rethrow;
  }

  if (kDebugMode) {
    final Session? session = Supabase.instance.client.auth.currentSession;
    debugPrint("[AUTH_DEBUG] bootstrap done: currentSession=${session != null}");
  }

  return AppDependencies.fromEnvironment();
}
