import "dart:convert";
import "package:flutter/foundation.dart";
import "package:flutter/material.dart";
import "package:flutter_dotenv/flutter_dotenv.dart";
import "package:http/http.dart" as http;
import "package:supabase_flutter/supabase_flutter.dart";
import "app_nav.dart";
import "config/app_config.dart";
import "pages/login_page.dart";
import "theme/app_theme.dart";
import "widgets/profu_drawer.dart";

void _authLog(String msg) {
  if (kDebugMode) debugPrint("[AUTH_DEBUG] $msg");
}

// #region agent log
/// Sends debug logs to the local Cursor agent ingestion endpoint for runtime analysis.
Future<void> _agentDebugLog({
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
// #endregion agent log

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Load .env on all platforms; on web the asset may be available when running via `poe ui` (flutter run -d chrome).
  try {
    if (kDebugMode) {
      debugPrint("[AGENT_DEBUG] main() starting dotenv.load (kIsWeb=$kIsWeb)");
    }
    await dotenv.load(fileName: ".env");
    if (kDebugMode) {
      debugPrint("[AGENT_DEBUG] dotenv.load completed successfully");
    }
    await _agentDebugLog(
      hypothesisId: kIsWeb ? "H2" : "H1",
      location: "flutter_app/lib/main.dart:main:dotenv.load",
      message: "dotenv.load completed successfully",
      data: <String, dynamic>{
        "fileName": ".env",
        "platform": kIsWeb ? "web" : "non-web",
        "envCount": dotenv.env.length,
      },
    );
  } catch (e, st) {
    debugPrint("[AGENT_DEBUG] dotenv.load failed: $e");
    await _agentDebugLog(
      hypothesisId: kIsWeb ? "H2" : "H1",
      location: "flutter_app/lib/main.dart:main:dotenv.load",
      message: "dotenv.load threw an error",
      data: <String, dynamic>{
        "fileName": ".env",
        "platform": kIsWeb ? "web" : "non-web",
        "error": e.toString(),
        "stackTrace": st.toString(),
      },
    );
    // On web, .env asset may be missing; AppConfig uses fallbacks for local Supabase.
  }
  try {
    debugPrint("[AGENT_DEBUG] main() starting Supabase.initialize");
    await Supabase.initialize(
      url: AppConfig.supabaseUrl,
      anonKey: AppConfig.supabaseAnonKey,
    );
    await _agentDebugLog(
      hypothesisId: "H3",
      location: "flutter_app/lib/main.dart:main:Supabase.initialize",
      message: "Supabase.initialize completed successfully",
      data: <String, dynamic>{
        "supabaseUrl": AppConfig.supabaseUrl,
        "hasAnonKey": AppConfig.supabaseAnonKey.isNotEmpty,
      },
    );
  } catch (e, st) {
    debugPrint("[AGENT_DEBUG] Supabase.initialize failed: $e");
    await _agentDebugLog(
      hypothesisId: "H3",
      location: "flutter_app/lib/main.dart:main:Supabase.initialize",
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
    final session = Supabase.instance.client.auth.currentSession;
    debugPrint("[AUTH_DEBUG] main() after init: currentSession=${session != null}");
  }
  runApp(const ProfuApp());
}


class ProfuApp extends StatefulWidget {
  const ProfuApp({super.key});

  @override
  State<ProfuApp> createState() => _ProfuAppState();
}

class _ProfuAppState extends State<ProfuApp> {
  @override
  void initState() {
    super.initState();
    Supabase.instance.client.auth.onAuthStateChange.listen((data) {
      _authLog('onAuthStateChange: ${data.event} (session=${data.session != null})');
      void navigate() {
        final target = data.event == AuthChangeEvent.signedIn ? '/' : '/login';
        final state = appNavigatorKey.currentState;
        _authLog('navigate() target=$target currentState=${state != null}');
        if (state == null) {
          _authLog('navigate() SKIP: navigator currentState is null');
          return;
        }
        state.pushNamedAndRemoveUntil(target, (route) => false);
        _authLog('navigate() pushNamedAndRemoveUntil done');
      }
      if (data.event == AuthChangeEvent.signedIn) {
        WidgetsBinding.instance.addPostFrameCallback((_) => navigate());
      } else if (data.event == AuthChangeEvent.signedOut) {
        navigate();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: appNavigatorKey,
      title: 'Profu',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: appDarkTheme,
      themeMode: ThemeMode.dark, // Force dark mode
      initialRoute: '/',
      routes: <String, WidgetBuilder>{
        '/': (context) {
          final hasSession = Supabase.instance.client.auth.currentSession != null;
          _authLog("route '/' build: hasSession=$hasSession");
          return hasSession ? const LandingPage() : const LoginPage();
        },
        '/login': (context) => const LoginPage(),
      },
    );
  }
}

class LandingPage extends StatefulWidget {
  const LandingPage({super.key});

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
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) return;
    try {
      final res = await Supabase.instance.client
          .from('users')
          .select('first_name, last_name')
          .eq('auth_id', user.id)
          .maybeSingle();
      if (!mounted) return;
      if (res != null) {
        final first = (res['first_name'] as String?)?.trim() ?? '';
        final last = (res['last_name'] as String?)?.trim() ?? '';
        final name = [first, last].where((s) => s.isNotEmpty).join(' ');
        setState(() {
          _displayName = name.isNotEmpty ? name : null;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _displayName = null);
    }
  }

  Future<void> _fetchAppDescription() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await http.get(Uri.parse('${AppConfig.apiBaseUrl}/index'));

      if (response.statusCode == 200) {
        setState(() {
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = 'Failed to load: ${response.statusCode}';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error connecting to server: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = Supabase.instance.client.auth.currentUser;
    final String greetingName = _displayName?.isNotEmpty == true
        ? _displayName!
        : (user?.email ?? 'Cont');
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profu'),
        centerTitle: true,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Text(
                'Salut, $greetingName',
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
                'imgs/gemini_gray.png',
                height: 180,
                fit: BoxFit.contain,
              ),
              const SizedBox(height: 32),
              Text(
                'Bine ai venit la Profu!',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Text(
                'Deschide meniul din stânga sus pentru a începe',
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
                  'Server offline',
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
                    const Text('Conectat la server'),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }

}
