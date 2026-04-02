import "package:profu_app/models/conversation_models.dart";
import "package:profu_app/services/conversation_repository_api.dart";

/// In-memory fake for widget / integration-style tests without Supabase.
class FakeConversationRepository implements ConversationRepositoryApi {
  /// Creates an empty fake repository.
  FakeConversationRepository();

  final List<Conversation> _conversations = <Conversation>[];
  final Map<int, List<ConversationMessage>> _messages = <int, List<ConversationMessage>>{};
  int _nextConvId = 1;
  int _nextMsgId = 1;

  @override
  Future<List<Conversation>> listConversations({
    required ConversationType type,
  }) async {
    return _conversations.where((Conversation c) => c.type == type).toList();
  }

  @override
  Future<List<ConversationMessage>> listMessages({
    required int conversationId,
  }) async {
    return List<ConversationMessage>.from(_messages[conversationId] ?? <ConversationMessage>[]);
  }

  @override
  Future<Conversation> createConversation({
    required ConversationType type,
    String? title,
    String? schoolSubject,
  }) async {
    final Conversation c = Conversation(
      id: _nextConvId++,
      userId: "test-user",
      type: type,
      createdAt: DateTime.utc(2025, 1, 1),
      title: title,
      schoolSubject: schoolSubject,
    );
    _conversations.insert(0, c);
    _messages[c.id] = <ConversationMessage>[];
    return c;
  }

  @override
  Future<Conversation> updateConversationTitle({
    required int conversationId,
    required String title,
  }) async {
    final int i = _conversations.indexWhere((Conversation c) => c.id == conversationId);
    if (i < 0) {
      throw StateError("conversation not found");
    }
    final Conversation old = _conversations[i];
    final Conversation updated = old.copyWith(name: title.trim().isEmpty ? null : title.trim());
    _conversations[i] = updated;
    return updated;
  }

  @override
  Future<void> deleteConversation({required int conversationId}) async {
    _conversations.removeWhere((Conversation c) => c.id == conversationId);
    _messages.remove(conversationId);
  }

  @override
  Future<ConversationMessage> createMessage({
    required int conversationId,
    required String speaker,
    required String content,
  }) async {
    final ConversationMessage m = ConversationMessage(
      id: _nextMsgId++,
      conversationId: conversationId,
      speaker: speaker,
      content: content,
      createdAt: DateTime.utc(2025, 1, 2),
    );
    _messages.putIfAbsent(conversationId, () => <ConversationMessage>[]).add(m);
    return m;
  }
}
