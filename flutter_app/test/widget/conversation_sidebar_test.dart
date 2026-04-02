import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:profu_app/models/conversation_models.dart";
import "package:profu_app/widgets/conversation_sidebar.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:supabase_flutter/supabase_flutter.dart";

import "../helpers/fake_conversation_repository.dart";

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await Supabase.initialize(
      url: "https://test.supabase.co",
      anonKey: "test-anon-key",
    );
  });

  testWidgets("ConversationSidebar lists conversations from fake repository", (WidgetTester tester) async {
    final FakeConversationRepository fake = FakeConversationRepository();
    await fake.createConversation(type: ConversationType.clarify, title: "T1");

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ConversationSidebar(
            type: ConversationType.clarify,
            repository: fake,
            selectedConversation: null,
            onConversationSelected: (_) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text("T1"), findsOneWidget);
  });
}
