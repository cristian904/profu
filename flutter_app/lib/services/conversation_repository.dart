import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/conversation_models.dart';

/// Repository for conversations and messages using Supabase client.
/// All operations use the current user's JWT; RLS restricts access to their data.
class ConversationRepository {
  ConversationRepository();

  SupabaseClient get _client => Supabase.instance.client;

  String? get _currentUserId => _client.auth.currentUser?.id;

  Future<List<Conversation>> listConversations({
    required ConversationType type,
  }) async {
    final response = await _client
        .from('conversations')
        .select()
        .eq('type', type.dbValue)
        .order('created_at', ascending: false);

    final List<dynamic> data = response as List<dynamic>;
    return data
        .map((e) => Conversation.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<ConversationMessage>> listMessages({
    required int conversationId,
  }) async {
    final response = await _client
        .from('conversation_messages')
        .select()
        .eq('conversation_id', conversationId)
        .order('created_at', ascending: true);

    final List<dynamic> data = response as List<dynamic>;
    return data
        .map((e) => ConversationMessage.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Conversation> createConversation({
    required ConversationType type,
    String? title,
    String? schoolSubject,
  }) async {
    final userId = _currentUserId;
    if (userId == null) {
      throw Exception('Must be logged in to create a conversation');
    }

    final response = await _client.from('conversations').insert({
      'user_id': userId,
      'type': type.dbValue,
      'title': title,
      'school_subject': schoolSubject,
    }).select().single();

    return Conversation.fromJson(response as Map<String, dynamic>);
  }

  Future<Conversation> updateConversationTitle({
    required int conversationId,
    required String title,
  }) async {
    final response = await _client
        .from('conversations')
        .update({'title': title})
        .eq('id', conversationId)
        .select()
        .single();

    return Conversation.fromJson(response as Map<String, dynamic>);
  }

  Future<ConversationMessage> createMessage({
    required int conversationId,
    required String speaker,
    required String content,
  }) async {
    final response = await _client.from('conversation_messages').insert({
      'conversation_id': conversationId,
      'speaker': speaker,
      'content': content,
    }).select().single();

    return ConversationMessage.fromJson(response as Map<String, dynamic>);
  }
}
