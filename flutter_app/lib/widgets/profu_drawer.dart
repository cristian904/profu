import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../pages/clarify_chat_page.dart';
import '../pages/simulation_page.dart';
import '../pages/solve_problem_page.dart';
import 'glass_panel.dart';
import 'profu_scene_background.dart';

class ProfuDrawer extends StatelessWidget {
  const ProfuDrawer({super.key});

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
    } else if (option == 'simulation') {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => const SimulationPage()),
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

  @override
  Widget build(BuildContext context) {
    final user = Supabase.instance.client.auth.currentUser;
    final displayLabel = user?.email ?? 'Cont';
    final scheme = Theme.of(context).colorScheme;

    return Drawer(
      child: ProfuSceneBackground(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
                child: GlassPanel(
                  blurSigma: 12,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Image.asset(
                        'imgs/logo_black.png',
                        height: 56,
                        fit: BoxFit.contain,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Meniu',
                        style: TextStyle(
                          color: scheme.onSurface,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        displayLabel,
                        style: TextStyle(
                          color: scheme.onSurface.withValues(alpha: 0.9),
                          fontSize: 12,
                        ),
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            ListTile(
              leading: Icon(Icons.help_outline, color: scheme.primary),
              title: const Text('N-am înțeles la clasă'),
              onTap: () => _handleMenuOption(context, 'clarify'),
            ),
            ListTile(
              leading: Icon(Icons.edit_note, color: scheme.primary),
              title: const Text('Vreau să rezolv o problemă'),
              onTap: () => _handleMenuOption(context, 'problem'),
            ),
            ListTile(
              leading: Icon(Icons.quiz, color: scheme.primary),
              title: const Text('Simulare'),
              onTap: () => _handleMenuOption(context, 'simulation'),
            ),
            const Divider(),
            ListTile(
              leading: Icon(Icons.logout, color: scheme.onSurfaceVariant),
              title: const Text('Deconectare'),
              onTap: () async {
                Navigator.pop(context);
                await Supabase.instance.client.auth.signOut();
                if (!context.mounted) return;
                Navigator.of(context).pushNamedAndRemoveUntil(
                  '/login',
                  (route) => false,
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

