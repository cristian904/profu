import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:http/http.dart" as http;
import "package:http/testing.dart";
import "package:profu_app/app/landing_page.dart";
import "package:profu_app/core/di/app_dependencies.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:supabase_flutter/supabase_flutter.dart";

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await Supabase.initialize(
      url: "https://test.supabase.co",
      anonKey: "test-anon-key",
    );
  });

  testWidgets("shows connected state when GET /index returns 200", (WidgetTester tester) async {
    final http.Client client = MockClient((http.BaseRequest request) async {
      expect(request.url.path, "/index");
      return http.Response("{}", 200);
    });

    final AppDependencies deps = AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: client,
      apiBaseUrl: "http://landing.test",
    );

    await tester.pumpWidget(
      MaterialApp(
        home: LandingPage(dependencies: deps),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("Conectat la server"), findsOneWidget);
  });

  testWidgets("shows server offline when HTTP client throws", (WidgetTester tester) async {
    final http.Client client = MockClient((_) async {
      throw Exception("network down");
    });

    final AppDependencies deps = AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: client,
      apiBaseUrl: "http://landing.test",
    );

    await tester.pumpWidget(
      MaterialApp(
        home: LandingPage(dependencies: deps),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("Server offline"), findsOneWidget);
  });

  testWidgets("shows server offline on non-200", (WidgetTester tester) async {
    final http.Client client = MockClient(
      (_) async => http.Response("err", 500),
    );

    final AppDependencies deps = AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: client,
      apiBaseUrl: "http://landing.test",
    );

    await tester.pumpWidget(
      MaterialApp(
        home: LandingPage(dependencies: deps),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("Server offline"), findsOneWidget);
  });
}
