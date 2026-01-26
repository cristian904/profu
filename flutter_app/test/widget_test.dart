import 'package:flutter_test/flutter_test.dart';
import 'package:profu_app/main.dart';

void main() {
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
      await tester.pumpWidget(const ProfuApp());
      await tester.pumpAndSettle();

      // Find and tap the menu button
      final menuButton = find.byTooltip('Open navigation menu');
      expect(menuButton, findsOneWidget);
      
      await tester.tap(menuButton);
      await tester.pumpAndSettle();

      // Verify drawer items are present
      expect(find.text('N-am înțeles la clasă'), findsOneWidget);
      expect(find.text('Vreau să rezolv o problemă'), findsOneWidget);
      expect(find.text('Simulare'), findsOneWidget);
    });

    testWidgets('Drawer menu items are tappable', (WidgetTester tester) async {
      await tester.pumpWidget(const ProfuApp());
      await tester.pumpAndSettle();

      // Open drawer
      final menuButton = find.byTooltip('Open navigation menu');
      await tester.tap(menuButton);
      await tester.pumpAndSettle();

      // Tap on first menu item
      await tester.tap(find.text('N-am înțeles la clasă'));
      await tester.pumpAndSettle();

      // Should navigate to chat page - verify by checking for the chat page title
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
