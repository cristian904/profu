import 'package:flutter_test/flutter_test.dart';
import 'package:profu_app/pages/clarify_chat_page.dart';
import 'package:flutter/material.dart';

void main() {
  group('ClarifyChatPage Tests', () {
    testWidgets('Chat page should build without errors', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );

      // Verify that the page builds
      expect(find.byType(ClarifyChatPage), findsOneWidget);
    });

    testWidgets('Chat page should have a title', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );

      // Verify title is present
      expect(find.text('N-am înțeles la clasă'), findsOneWidget);
    });

    testWidgets('Chat page should have two tabs', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );

      // Verify both tabs are present
      expect(find.text('Explica'), findsOneWidget);
      expect(find.text('Învățat pas cu pas'), findsOneWidget);
      expect(find.byType(TabBar), findsOneWidget);
      expect(find.byType(TabBarView), findsOneWidget);
    });

    testWidgets('Explica tab should have a text input field', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );
      await tester.pumpAndSettle();

      // Default tab should be Explica (first tab)
      // Verify text field exists (should find 2 - one in each tab, but only first is visible)
      expect(find.byType(TextField), findsWidgets);
    });

    testWidgets('Explica tab should have a send button', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );
      await tester.pumpAndSettle();

      // Verify send button exists (should find 2 - one in each tab, but only first is visible)
      expect(find.byIcon(Icons.send), findsWidgets);
    });

    testWidgets('User can switch between tabs', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );
      await tester.pumpAndSettle();

      // Initially on Explica tab
      expect(find.text('Pune o întrebare despre ce nu ai înțeles!'), findsOneWidget);
      expect(find.byIcon(Icons.help_outline), findsOneWidget);

      // Tap on "Învățat pas cu pas" tab
      await tester.tap(find.text('Învățat pas cu pas'));
      await tester.pumpAndSettle();

      // Verify we're on the guided learning tab
      expect(find.text('Pune o întrebare și te voi ghida pas cu pas să înțelegi conceptul!'), findsOneWidget);
      expect(find.byIcon(Icons.school_outlined), findsOneWidget);
    });

    testWidgets('User can type in the text field on Explica tab', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );
      await tester.pumpAndSettle();

      // Find the text field (first one visible in Explica tab)
      final textField = find.byType(TextField).first;
      
      // Enter text
      await tester.enterText(textField, 'Test message');
      await tester.pump();

      // Verify text was entered
      expect(find.text('Test message'), findsOneWidget);
    });

    testWidgets('Explica tab shows welcome message initially', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );
      await tester.pumpAndSettle();

      // Verify welcome message is shown when no messages exist
      expect(find.text('Pune o întrebare despre ce nu ai înțeles!'), findsOneWidget);
      expect(find.byIcon(Icons.help_outline), findsOneWidget);
    });

    testWidgets('Guided learning tab shows welcome message initially', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClarifyChatPage(),
        ),
      );
      await tester.pumpAndSettle();

      // Switch to guided learning tab
      await tester.tap(find.text('Învățat pas cu pas'));
      await tester.pumpAndSettle();

      // Verify welcome message is shown
      expect(find.text('Pune o întrebare și te voi ghida pas cu pas să înțelegi conceptul!'), findsOneWidget);
      expect(find.byIcon(Icons.school_outlined), findsOneWidget);
    });
  });

  group('ChatMessage Model Tests', () {
    test('ChatMessage should store message data correctly', () {
      final message = ChatMessage(
        text: 'Test message',
        isUser: true,
        timestamp: DateTime.now(),
      );

      expect(message.text, 'Test message');
      expect(message.isUser, true);
      expect(message.isStreaming, false);
    });

    test('ChatMessage should handle streaming state', () {
      final message = ChatMessage(
        text: 'Streaming...',
        isUser: false,
        timestamp: DateTime.now(),
        isStreaming: true,
      );

      expect(message.text, 'Streaming...');
      expect(message.isUser, false);
      expect(message.isStreaming, true);
    });
  });
}
