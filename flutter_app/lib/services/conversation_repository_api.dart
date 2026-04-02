import "../models/conversation_models.dart";

/// Contract for conversation persistence (Supabase-backed impl or fakes in tests).
abstract class ConversationRepositoryApi {
  /// Lists conversations for the signed-in user filtered by [type].
  Future<List<Conversation>> listConversations({
    required ConversationType type,
  });

  /// Loads messages for a conversation in chronological order.
  Future<List<ConversationMessage>> listMessages({
    required int conversationId,
  });

  /// Creates a new conversation row.
  Future<Conversation> createConversation({
    required ConversationType type,
    String? title,
    String? schoolSubject,
  });

  /// Updates the user-visible name (empty clears custom name).
  Future<Conversation> updateConversationTitle({
    required int conversationId,
    required String title,
  });

  /// Deletes a conversation (cascade messages per DB rules).
  Future<void> deleteConversation({required int conversationId});

  /// Appends a message to a conversation.
  Future<ConversationMessage> createMessage({
    required int conversationId,
    required String speaker,
    required String content,
  });
}
