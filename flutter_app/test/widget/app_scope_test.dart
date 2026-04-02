import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:http/http.dart" as http;
import "package:profu_app/core/di/app_dependencies.dart";
import "package:profu_app/core/di/app_scope.dart";
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

  testWidgets("AppScope updateShouldNotify when dependencies instance changes", (WidgetTester tester) async {
    final AppDependencies depsA = AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: http.Client(),
      apiBaseUrl: "http://a",
    );
    final AppDependencies depsB = AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: http.Client(),
      apiBaseUrl: "http://b",
    );

    await tester.pumpWidget(
      AppScope(
        dependencies: depsA,
        child: const SizedBox.shrink(),
      ),
    );
    final AppScope first = tester.widget<AppScope>(find.byType(AppScope));

    await tester.pumpWidget(
      AppScope(
        dependencies: depsB,
        child: const SizedBox.shrink(),
      ),
    );
    final AppScope second = tester.widget<AppScope>(find.byType(AppScope));

    expect(second.updateShouldNotify(first), isTrue);
    depsA.httpClient.close();
    depsB.httpClient.close();
  });

  testWidgets("AppScope.of returns injected dependencies", (WidgetTester tester) async {
    final AppDependencies deps = AppDependencies(
      supabase: Supabase.instance.client,
      httpClient: http.Client(),
      apiBaseUrl: "http://scope.test",
    );

    late AppDependencies read;

    await tester.pumpWidget(
      AppScope(
        dependencies: deps,
        child: Builder(
          builder: (BuildContext context) {
            read = AppScope.of(context);
            return const SizedBox.shrink();
          },
        ),
      ),
    );

    expect(read.apiBaseUrl, "http://scope.test");
    deps.httpClient.close();
  });
}
