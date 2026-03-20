import "package:flutter/foundation.dart";
import "package:flutter/material.dart";
import "dart:convert";
import "package:http/http.dart" as http;
import "package:supabase_flutter/supabase_flutter.dart";

import "../config/app_config.dart";
import "../widgets/profu_drawer.dart";

/// Simulari page with the two required tabs: Istoric and Simulare.
class SimulationPage extends StatefulWidget {
  /// Creates the Simulari page.
  const SimulationPage({super.key});

  @override
  State<SimulationPage> createState() => _SimulationPageState();
}

class _SimulationPageState extends State<SimulationPage> with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  bool _isGenerating = false;
  int? _lastSimulationId;

  @override
  void initState() {
    super.initState();
    // Initialize tab controller for "Istoric" and "Simulare".
    _tabController = TabController(length: 2, vsync: this);
    if (kDebugMode) {
      debugPrint("[SIMULARI_UI] SimulationPage initialized");
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  /// Calls backend endpoint to create a new simulation and shows user feedback.
  Future<void> _onGeneratePressed() async {
    if (_isGenerating) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate ignored: request already in progress");
      }
      return;
    }

    setState(() {
      _isGenerating = true;
    });

    try {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate button pressed");
      }

      final String? accessToken = Supabase.instance.client.auth.currentSession?.accessToken;
      if (accessToken == null || accessToken.isEmpty) {
        throw Exception("Missing auth session. Please sign in again.");
      }

      final Uri endpoint = Uri.parse("${AppConfig.apiBaseUrl}/simulari/generate");
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Calling endpoint: $endpoint");
      }

      final http.Response response = await http.post(
        endpoint,
        headers: <String, String>{
          "Content-Type": "application/json",
          "Authorization": "Bearer $accessToken",
        },
        body: jsonEncode(<String, dynamic>{
          "school_subject": "math",
        }),
      );

      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate response status: ${response.statusCode}");
        debugPrint("[SIMULARI_UI] Generate response body: ${response.body}");
      }

      if (response.statusCode != 201) {
        String errorMessage = "Nu am putut genera simularea.";
        try {
          final Map<String, dynamic> payload = jsonDecode(response.body) as Map<String, dynamic>;
          final dynamic detail = payload["detail"];
          if (detail != null && detail.toString().isNotEmpty) {
            errorMessage = detail.toString();
          }
        } catch (_) {
          // Keep default message if body is not valid JSON.
        }
        throw Exception(errorMessage);
      }

      final Map<String, dynamic> payload = jsonDecode(response.body) as Map<String, dynamic>;
      final int simulationId = payload["simulation_id"] as int;
      setState(() {
        _lastSimulationId = simulationId;
      });

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Simulare generata cu succes. ID: $simulationId"),
        ),
      );
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate error: $error");
        debugPrint("[SIMULARI_UI] Generate stack: $stackTrace");
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Eroare la generare: $error"),
        ),
      );
    } finally {
      if (!mounted) return;
      setState(() {
        _isGenerating = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Simulari"),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: "Istoric"),
            Tab(text: "Simulare"),
          ],
        ),
      ),
      drawer: const ProfuDrawer(),
      body: TabBarView(
        controller: _tabController,
        children: [
          Center(
            child: Text(
              "Istoricul simularilor va fi afisat aici.",
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
          ),
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                ElevatedButton(
                  onPressed: _isGenerating ? null : _onGeneratePressed,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 20),
                  ),
                  child: _isGenerating
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text("Genereaza"),
                ),
                const SizedBox(height: 16),
                if (_lastSimulationId != null)
                  Text(
                    "Ultima simulare generata: #$_lastSimulationId",
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

