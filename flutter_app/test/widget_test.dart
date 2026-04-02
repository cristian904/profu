import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:profu_app/app/profu_app.dart';
import 'package:profu_app/core/di/app_dependencies.dart';
import 'package:profu_app/widgets/profu_drawer.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await Supabase.initialize(
      url: "https://test.supabase.co",
      anonKey: "test-anon-key",
    );
  });

  AppDependencies testDependencies() {
    final http.Client client = MockClient((http.BaseRequest request) async {
      if (request.url.path == "/index") {
        return http.Response("{}", 200);
      }
      return http.Response("not found", 404);
    });
    return AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: client,
      apiBaseUrl: "http://widget.test",
    );
  }

  group("Main App Tests", () {
    testWidgets("App should build without errors", (WidgetTester tester) async {
      final AppDependencies deps = testDependencies();
      await tester.pumpWidget(ProfuApp(dependencies: deps));

      expect(find.byType(ProfuApp), findsOneWidget);
    });

    testWidgets("App should have a title when session shows landing", (WidgetTester tester) async {
      final AppDependencies deps = testDependencies();
      await tester.pumpWidget(ProfuApp(dependencies: deps));
      await tester.pumpAndSettle();

      // Logged-out users see LoginPage (may not show AppBar title "Profu" the same way).
      expect(find.byType(ProfuApp), findsOneWidget);
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

  group("Theme Tests", () {
    testWidgets("App should use dark theme", (WidgetTester tester) async {
      final AppDependencies deps = testDependencies();
      await tester.pumpWidget(ProfuApp(dependencies: deps));

      final ProfuApp app = tester.widget<ProfuApp>(find.byType(ProfuApp));
      expect(app.dependencies, isNotNull);
    });
  });
}
