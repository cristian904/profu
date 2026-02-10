import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../pages/clarify_chat_page.dart';
import '../pages/solve_problem_page.dart';

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

    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primary,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.school,
                  size: 60,
                  color: Colors.white,
                ),
                const SizedBox(height: 16),
                const Text(
                  'Meniu',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  displayLabel,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    fontSize: 14,
                  ),
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
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
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.grey),
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
    );
  }
}

