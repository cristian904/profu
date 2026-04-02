import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:profu_app/theme/app_theme.dart";

void main() {
  testWidgets("appDarkTheme applies to MaterialApp", (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: appDarkTheme,
        home: const Scaffold(
          body: Text("body"),
        ),
      ),
    );

    final ThemeData theme = Theme.of(tester.element(find.text("body")));
    expect(theme.brightness, Brightness.dark);
  });
}
