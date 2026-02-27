import 'package:flutter/foundation.dart';

/// Conversation types stored in `public.conversations.type`.
enum ConversationType {
  problemSolving,
  clarify,
  clarifySteps,
}

extension ConversationTypeDb on ConversationType {
  String get dbValue {
    switch (this) {
      case ConversationType.problemSolving:
        return 'problem_solving';
      case ConversationType.clarify:
        return 'clarify';
      case ConversationType.clarifySteps:
        return 'clarify_steps';
    }
  }

  static ConversationType fromDb(String value) {
    switch (value) {
      case 'problem_solving':
        return ConversationType.problemSolving;
      case 'clarify':
        return ConversationType.clarify;
      case 'clarify_steps':
        return ConversationType.clarifySteps;
      default:
        debugPrint('Unknown conversation type: $value, defaulting to clarify');
        return ConversationType.clarify;
    }
  }
}

/// Speaker field in `conversation_messages.speaker`.
class ConversationSpeaker {
  static const String user = 'user';
  static const String assistant = 'assistant';
}

class Conversation {
  final int id;
  final String userId;
  final String? name;
  final String? title;
  final String? schoolSubject;
  final ConversationType type;
  final DateTime createdAt;

  Conversation({
    required this.id,
    required this.userId,
    required this.type,
    required this.createdAt,
    this.name,
    this.title,
    this.schoolSubject,
  });

  factory Conversation.fromJson(Map<String, dynamic> json) {
    return Conversation(
      id: json['id'] as int,
      userId: json['user_id'] as String,
      name: json['name'] as String?,
      title: json['title'] as String?,
      schoolSubject: json['school_subject'] as String?,
      type: ConversationTypeDb.fromDb(json['type'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  Conversation copyWith({
    String? name,
    String? title,
    String? schoolSubject,
    ConversationType? type,
  }) {
    return Conversation(
      id: id,
      userId: userId,
      name: name ?? this.name,
      title: title ?? this.title,
      schoolSubject: schoolSubject ?? this.schoolSubject,
      type: type ?? this.type,
      createdAt: createdAt,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'user_id': userId,
      'name': name,
      'title': title,
      'school_subject': schoolSubject,
      'type': type.dbValue,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

class ConversationMessage {
  final int id;
  final int conversationId;
  final String speaker;
  final String? content;
  final DateTime createdAt;

  ConversationMessage({
    required this.id,
    required this.conversationId,
    required this.speaker,
    required this.createdAt,
    this.content,
  });

  factory ConversationMessage.fromJson(Map<String, dynamic> json) {
    return ConversationMessage(
      id: json['id'] as int,
      conversationId: json['conversation_id'] as int,
      speaker: json['speaker'] as String,
      content: json['content'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'conversation_id': conversationId,
      'speaker': speaker,
      'content': content,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

