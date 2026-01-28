import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/conversation_models.dart';
import '../supabase_rest_config.dart';

/// Repository responsible for talking to Supabase REST about
/// conversations and conversation messages.
class ConversationRepository {
  ConversationRepository();

  /// For now, all conversations are stored under this fixed user id.
  /// Replace with the authenticated user id in the future.
  static const int _testUserId = 1;

  Uri _buildUri(String path, [Map<String, String>? query]) {
    final base = supabaseRestUrl.endsWith('/')
        ? supabaseRestUrl.substring(0, supabaseRestUrl.length - 1)
        : supabaseRestUrl;
    return Uri.parse('$base/$path').replace(queryParameters: query);
  }

  Map<String, String> _headers({Map<String, String>? extra}) {
    final base = supabaseBaseHeaders();
    if (extra != null) {
      base.addAll(extra);
    }
    return base;
  }

  Future<List<Conversation>> listConversations({
    required ConversationType type,
  }) async {
    final uri = _buildUri('conversations', <String, String>{
      'user_id': 'eq.$_testUserId',
      'type': 'eq.${type.dbValue}',
      'order': 'created_at.desc',
    });

    final response = await http.get(uri, headers: _headers());
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final List<dynamic> data = json.decode(response.body) as List<dynamic>;
      return data
          .map((e) => Conversation.fromJson(e as Map<String, dynamic>))
          .toList();
    }

    if (isDebugBuild) {
      debugPrint(
          'listConversations failed: ${response.statusCode} ${response.body}');
    }
    throw Exception('Failed to load conversations');
  }

  Future<List<ConversationMessage>> listMessages({
    required int conversationId,
  }) async {
    final uri = _buildUri('conversation_messages', <String, String>{
      'conversation_id': 'eq.$conversationId',
      'order': 'created_at.asc',
    });

    final response = await http.get(uri, headers: _headers());
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final List<dynamic> data = json.decode(response.body) as List<dynamic>;
      return data
          .map((e) => ConversationMessage.fromJson(e as Map<String, dynamic>))
          .toList();
    }

    if (isDebugBuild) {
      debugPrint(
          'listMessages failed: ${response.statusCode} ${response.body}');
    }
    throw Exception('Failed to load conversation messages');
  }

  Future<Conversation> createConversation({
    required ConversationType type,
    String? title,
    String? schoolSubject,
  }) async {
    final uri = _buildUri('conversations');
    final body = json.encode(<String, dynamic>{
      'user_id': _testUserId,
      'type': type.dbValue,
      'title': title,
      'school_subject': schoolSubject,
    });

    final response = await http.post(
      uri,
      headers: _headers(extra: const {'Prefer': 'return=representation'}),
      body: body,
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final decoded = json.decode(response.body);
      if (decoded is List && decoded.isNotEmpty) {
        return Conversation.fromJson(
            decoded.first as Map<String, dynamic>);
      } else if (decoded is Map<String, dynamic>) {
        return Conversation.fromJson(decoded);
      }
    }

    if (isDebugBuild) {
      debugPrint(
          'createConversation failed: ${response.statusCode} ${response.body}');
    }
    throw Exception('Failed to create conversation');
  }

  Future<Conversation> updateConversationTitle({
    required int conversationId,
    required String title,
  }) async {
    final uri = _buildUri('conversations', <String, String>{
      'id': 'eq.$conversationId',
    });
    final body = json.encode(<String, dynamic>{
      'title': title,
    });

    final response = await http.patch(
      uri,
      headers: _headers(extra: const {'Prefer': 'return=representation'}),
      body: body,
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final decoded = json.decode(response.body);
      if (decoded is List && decoded.isNotEmpty) {
        return Conversation.fromJson(decoded.first as Map<String, dynamic>);
      } else if (decoded is Map<String, dynamic>) {
        return Conversation.fromJson(decoded);
      }
    }

    if (isDebugBuild) {
      debugPrint(
          'updateConversationTitle failed: ${response.statusCode} ${response.body}');
    }
    throw Exception('Failed to update conversation title');
  }

  Future<ConversationMessage> createMessage({
    required int conversationId,
    required String speaker,
    required String content,
  }) async {
    final uri = _buildUri('conversation_messages');
    final body = json.encode(<String, dynamic>{
      'conversation_id': conversationId,
      'speaker': speaker,
      'content': content,
    });

    final response = await http.post(
      uri,
      headers: _headers(extra: const {'Prefer': 'return=representation'}),
      body: body,
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final decoded = json.decode(response.body);
      if (decoded is List && decoded.isNotEmpty) {
        return ConversationMessage.fromJson(
            decoded.first as Map<String, dynamic>);
      } else if (decoded is Map<String, dynamic>) {
        return ConversationMessage.fromJson(decoded);
      }
    }

    if (isDebugBuild) {
      debugPrint(
          'createMessage failed: ${response.statusCode} ${response.body}');
    }
    throw Exception('Failed to create conversation message');
  }
}

