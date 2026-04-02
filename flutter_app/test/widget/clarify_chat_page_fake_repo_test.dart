import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:profu_app/pages/clarify_chat_page.dart";
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

  testWidgets("ClarifyChatPage builds with fake repository", (WidgetTester tester) async {
    final FakeConversationRepository fake = FakeConversationRepository();

    await tester.pumpWidget(
      MaterialApp(
        home: ClarifyChatPage(
          conversationRepository: fake,
          apiBaseUrl: "http://localhost:9",
        ),
      ),
    );

    expect(find.byType(ClarifyChatPage), findsOneWidget);
    expect(find.text("N-am înțeles la clasă"), findsOneWidget);
  });
}
