import "package:flutter/material.dart";
import "package:http/http.dart" as http;
import "package:supabase_flutter/supabase_flutter.dart";
import "pages/clarify_chat_page.dart";
import "pages/solve_problem_page.dart";

/// Local Supabase URL and anon key. After running `npx supabase start` in the
/// repo root, copy the API URL and anon key from the CLI output (or from
/// supabase/.temp/env) and replace these placeholders.
const String _supabaseUrl = "http://127.0.0.1:54321";
const String _supabaseAnonKey = "YOUR_ANON_KEY"; // Replace with output of: npx supabase start

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Supabase.initialize(
    url: _supabaseUrl,
    anonKey: _supabaseAnonKey,
  );
  runApp(const ProfuApp());
}

class ProfuApp extends StatelessWidget {
  const ProfuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Profu',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF121212),
        cardTheme: const CardThemeData(
          color: Color(0xFF1E1E1E),
          elevation: 2,
        ),
        drawerTheme: const DrawerThemeData(
          backgroundColor: Color(0xFF1E1E1E),
        ),
      ),
      themeMode: ThemeMode.dark, // Force dark mode
      home: const LandingPage(),
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

  // Update this URL to match your FastAPI backend
  final String _apiUrl = 'http://localhost:8000/index';

  @override
  void initState() {
    super.initState();
    _fetchAppDescription();
  }

  Future<void> _fetchAppDescription() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await http.get(Uri.parse(_apiUrl));

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
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Profu'),
        centerTitle: true,
      ),
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
              ),
              child: const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.school,
                    size: 60,
                    color: Colors.white,
                  ),
                  SizedBox(height: 16),
                  Text(
                    'Meniu',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.help_outline, color: Colors.orange),
              title: const Text('N-am înțeles la clasă'),
              onTap: () => _handleMenuOption(context, 'clarify'),
            ),
            ListTile(
              leading: const Icon(Icons.edit_note, color: Colors.green),
              title: const Text('Vreau să rezolv o problemă'),
              onTap: () => _handleMenuOption(context, 'problem'),
            ),
            ListTile(
              leading: const Icon(Icons.quiz, color: Colors.purple),
              title: const Text('Simulare'),
              onTap: () => _handleMenuOption(context, 'simulation'),
            ),
          ],
        ),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.school,
                size: 100,
                color: Colors.blue,
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
                  style: TextStyle(color: Colors.red[700]),
                )
              else
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.check_circle, size: 20, color: Colors.green[600]),
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

  void _handleMenuOption(BuildContext context, String option) {
    Navigator.pop(context); // Close drawer
    
    if (option == 'clarify') {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => const ClarifyChatPage()),
      );
    } else if (option == 'problem') {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => const SolveProblemPage()),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Ai selectat: $option'),
          duration: const Duration(seconds: 2),
        ),
      );
      // TODO: Navigate to the appropriate screen based on option
    }
  }
}
