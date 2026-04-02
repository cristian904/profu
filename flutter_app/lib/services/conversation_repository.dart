import 'dart:convert';

import 'package:http/http.dart' as dbg_http;
import 'package:supabase_flutter/supabase_flutter.dart';

import "../models/conversation_models.dart";
import "conversation_repository_api.dart";

/// Repository for conversations and messages using Supabase client.
/// All operations use the current user's JWT; RLS restricts access to their data.
class ConversationRepository implements ConversationRepositoryApi {
  /// Uses [client] or falls back to the global Supabase instance.
  ConversationRepository({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;

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

    // #region agent log
    try {
      await dbg_http
          .post(
            Uri.parse(
                'http://127.0.0.1:7242/ingest/3b1cec4a-02ef-4628-8cc6-fd6744479f32'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'id': 'log_${DateTime.now().millisecondsSinceEpoch}',
              'timestamp': DateTime.now().millisecondsSinceEpoch,
              'location':
                  'conversation_repository.dart:createConversation:beforeInsert',
              'message': 'Create conversation attempt',
              'runId': 'pre-fix',
              'hypothesisId': 'H1_H2_H5',
              'data': {
                'hasUser': true,
                'userId': userId,
                'type': type.dbValue,
                'hasTitle': title?.isNotEmpty == true,
                'hasSchoolSubject': schoolSubject?.isNotEmpty == true,
              },
            }),
          )
          .catchError((_) {});
    } catch (_) {
      // ignore logging failures
    }
    // #endregion agent log

    try {
      final response = await _client.from('conversations').insert({
        'user_id': userId,
        'type': type.dbValue,
        'title': title,
        'school_subject': schoolSubject,
        // `name` is reserved for optional user-defined title set via rename.
        // For new conversations we keep it null so UI falls back to first message/title.
      }).select().single();

      return Conversation.fromJson(response as Map<String, dynamic>);
    } catch (e) {
      // #region agent log
      try {
        await dbg_http
            .post(
              Uri.parse(
                  'http://127.0.0.1:7242/ingest/3b1cec4a-02ef-4628-8cc6-fd6744479f32'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({
                'id': 'log_${DateTime.now().millisecondsSinceEpoch}',
                'timestamp': DateTime.now().millisecondsSinceEpoch,
                'location':
                    'conversation_repository.dart:createConversation:error',
                'message': 'Create conversation error',
                'runId': 'pre-fix',
                'hypothesisId': 'H1_H2_H5',
                'data': {
                  'userId': userId,
                  'error': e.toString(),
                },
              }),
            )
            .catchError((_) {});
      } catch (_) {
        // ignore logging failures
      }
      // #endregion agent log
      rethrow;
    }
  }

  Future<Conversation> updateConversationTitle({
    required int conversationId,
    required String title,
  }) async {
    // Treat empty/whitespace-only titles as clearing the custom name (store NULL).
    final normalizedTitle = title.trim().isEmpty ? null : title.trim();

    final response = await _client
        .from('conversations')
        // Store user-defined titles in `name`. Null means "no custom name".
        .update({'name': normalizedTitle})
        .eq('id', conversationId)
        .select()
        .single();

    return Conversation.fromJson(response as Map<String, dynamic>);
  }

  Future<void> deleteConversation({required int conversationId}) async {
    await _client
        .from('conversations')
        .delete()
        .eq('id', conversationId);
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
