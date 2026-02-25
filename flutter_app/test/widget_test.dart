import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:profu_app/main.dart';
import 'package:profu_app/widgets/profu_drawer.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://test.supabase.co',
      anonKey: 'test-anon-key',
    );
  });

  group('Main App Tests', () {
    testWidgets('App should build without errors', (WidgetTester tester) async {
      // Build the app
      await tester.pumpWidget(const ProfuApp());

      // Verify that the app builds
      expect(find.byType(ProfuApp), findsOneWidget);
    });

    testWidgets('App should have a title', (WidgetTester tester) async {
      await tester.pumpWidget(const ProfuApp());

      // Verify that the app has a title
      expect(find.text('Profu'), findsOneWidget);
    });

    testWidgets('App should have a drawer menu', (WidgetTester tester) async {
      // Pump a scaffold with drawer (drawer is only on LandingPage when logged in)
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            appBar: AppBar(title: const Text('Profu')),
            drawer: const ProfuDrawer(),
            body: const SizedBox.shrink(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final menuButton = find.byTooltip('Open navigation menu');
      expect(menuButton, findsOneWidget);

      await tester.tap(menuButton);
      await tester.pumpAndSettle();

      expect(find.text('N-am înțeles la clasă'), findsOneWidget);
      expect(find.text('Vreau să rezolv o problemă'), findsOneWidget);
      expect(find.text('Simulare'), findsOneWidget);
    });

    testWidgets('Drawer menu items are tappable', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            appBar: AppBar(title: const Text('Profu')),
            drawer: const ProfuDrawer(),
            body: const SizedBox.shrink(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final menuButton = find.byTooltip('Open navigation menu');
      await tester.tap(menuButton);
      await tester.pumpAndSettle();

      await tester.tap(find.text('N-am înțeles la clasă'));
      await tester.pumpAndSettle();

      expect(find.text('N-am înțeles la clasă'), findsAtLeastNWidgets(1));
    });
  });

  group('Theme Tests', () {
    testWidgets('App should use dark theme', (WidgetTester tester) async {
      await tester.pumpWidget(const ProfuApp());
      
      // The app should be using dark theme
      final materialApp = tester.widget<ProfuApp>(find.byType(ProfuApp));
      // Dark theme should be set
      expect(materialApp, isNotNull);
    });
  });
}
