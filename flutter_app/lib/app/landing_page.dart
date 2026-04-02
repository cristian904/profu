import "package:flutter/material.dart";
import "package:http/http.dart" as http;

import "../core/di/app_dependencies.dart";
import "../widgets/profu_drawer.dart";

/// Home shell after sign-in: health check to API and greeting from profile.
class LandingPage extends StatefulWidget {
  /// Creates the landing page using shared [dependencies].
  const LandingPage({super.key, required this.dependencies});

  /// HTTP + Supabase + API base URL.
  final AppDependencies dependencies;

  @override
  State<LandingPage> createState() => _LandingPageState();
}

class _LandingPageState extends State<LandingPage> {
  bool _isLoading = false;
  String? _error;
  String? _displayName;

  @override
  void initState() {
    super.initState();
    _fetchAppDescription();
    _fetchUserDisplayName();
  }

  Future<void> _fetchUserDisplayName() async {
    final user = widget.dependencies.supabase.auth.currentUser;
    if (user == null) {
      return;
    }
    try {
      final res = await widget.dependencies.supabase
          .from("users")
          .select("first_name, last_name")
          .eq("auth_id", user.id)
          .maybeSingle();
      if (!mounted) {
        return;
      }
      if (res != null) {
        final first = (res["first_name"] as String?)?.trim() ?? "";
        final last = (res["last_name"] as String?)?.trim() ?? "";
        final name = [first, last].where((String s) => s.isNotEmpty).join(" ");
        setState(() {
          _displayName = name.isNotEmpty ? name : null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _displayName = null);
      }
    }
  }

  Future<void> _fetchAppDescription() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final http.Response response = await widget.dependencies.httpClient
          .get(Uri.parse("${widget.dependencies.apiBaseUrl}/index"));

      if (response.statusCode == 200) {
        setState(() {
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = "Failed to load: ${response.statusCode}";
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = "Error connecting to server: $e";
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.dependencies.supabase.auth.currentUser;
    final String greetingName = _displayName?.isNotEmpty == true
        ? _displayName!
        : (user?.email ?? "Cont");
    return Scaffold(
      appBar: AppBar(
        title: const Text("Profu"),
        centerTitle: true,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Text(
                "Salut, $greetingName",
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
              ),
            ),
          ),
        ],
      ),
      drawer: const ProfuDrawer(),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Image.asset(
                "imgs/gemini_gray.png",
                height: 180,
                fit: BoxFit.contain,
              ),
              const SizedBox(height: 32),
              Text(
                "Bine ai venit la Profu!",
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Text(
                "Deschide meniul din stânga sus pentru a începe",
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              if (_isLoading)
                const CircularProgressIndicator()
              else if (_error != null)
                Text(
                  "Server offline",
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                )
              else
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.check_circle,
                      size: 20,
                      color: Colors.green[400],
                    ),
                    const SizedBox(width: 8),
                    const Text("Conectat la server"),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}
