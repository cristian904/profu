import "package:flutter_test/flutter_test.dart";
import "package:profu_app/models/conversation_models.dart";
import "package:profu_app/services/conversation_repository.dart";
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

  test("createConversation throws when no signed-in user", () async {
    final ConversationRepository repo = ConversationRepository(
      client: Supabase.instance.client,
    );
    expect(
      () => repo.createConversation(type: ConversationType.clarify),
      throwsA(isA<Exception>().having(
        (Exception e) => e.toString(),
        "message",
        contains("logged in"),
      )),
    );
  });
}
