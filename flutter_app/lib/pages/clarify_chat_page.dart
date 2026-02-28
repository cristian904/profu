import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:fl_chart/fl_chart.dart';
import 'package:math_expressions/math_expressions.dart';

import 'package:supabase_flutter/supabase_flutter.dart';

import '../config/app_config.dart';
import '../models/conversation_models.dart';
import '../services/conversation_repository.dart';
import '../widgets/conversation_sidebar.dart';
import '../widgets/profu_drawer.dart';

class ClarifyChatPage extends StatefulWidget {
  const ClarifyChatPage({super.key});

  @override
  State<ClarifyChatPage> createState() => _ClarifyChatPageState();
}

class _ClarifyChatPageState extends State<ClarifyChatPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('N-am înțeles la clasă'),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Explica'),
            Tab(text: 'Învățat pas cu pas'),
          ],
        ),
      ),
      drawer: const ProfuDrawer(),
      body: TabBarView(
        controller: _tabController,
        children: const [
          ExplicaTab(),
          GuidedLearningTab(),
        ],
      ),
    );
  }
}

// Explica Tab - Direct answers mode
class ExplicaTab extends StatefulWidget {
  const ExplicaTab({super.key});

  @override
  State<ExplicaTab> createState() => _ExplicaTabState();
}

class _ExplicaTabState extends State<ExplicaTab> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isStreaming = false;

  final ConversationRepository _conversationRepository = ConversationRepository();
  Conversation? _activeConversation;
  int? _conversationId;
  bool _isLoadingHistory = false;

  String get _apiUrl => '${AppConfig.apiBaseUrl}/clarify/once-stream';

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _ensureConversationCreated(String firstUserMessage) async {
    if (_conversationId != null) return;

    final title = firstUserMessage.trim().isEmpty
        ? null
        : (firstUserMessage.trim().length > 80
            ? '${firstUserMessage.trim().substring(0, 80)}...'
            : firstUserMessage.trim());

    final conv = await _conversationRepository.createConversation(
      type: ConversationType.clarify,
      title: title,
    );

    if (!mounted) return;
    setState(() {
      _activeConversation = conv;
      _conversationId = conv.id;
    });
  }

  Future<void> _loadConversationHistory(Conversation conversation) async {
    setState(() {
      _isLoadingHistory = true;
      _isStreaming = false;
    });

    try {
      final messages = await _conversationRepository.listMessages(
        conversationId: conversation.id,
      );

      if (!mounted) return;

      setState(() {
        _messages
          ..clear()
          ..addAll(
            messages.map(
              (m) => ChatMessage(
                text: m.content ?? '',
                isUser: m.speaker == ConversationSpeaker.user,
                timestamp: m.createdAt,
              ),
            ),
          );
        _activeConversation = conversation;
        _conversationId = conversation.id;
      });
      _scrollToBottom();
    } finally {
      if (!mounted) return;
      setState(() {
        _isLoadingHistory = false;
      });
    }
  }

  Future<void> _sendMessage() async {
    final message = _messageController.text.trim();
    if (message.isEmpty || _isStreaming) return;

    // Add user message
    setState(() {
      _messages.add(ChatMessage(
        text: message,
        isUser: true,
        timestamp: DateTime.now(),
      ));
      _isStreaming = true;
    });

    _messageController.clear();
    _scrollToBottom();

    // Ensure a conversation exists for this thread
    try {
      await _ensureConversationCreated(message);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Nu am putut crea conversația: $e')),
        );
      }
    }

    // Fire-and-forget: store the user message
    if (_conversationId != null) {
      _conversationRepository
          .createMessage(
            conversationId: _conversationId!,
            speaker: ConversationSpeaker.user,
            content: message,
          )
          .then((_) {}, onError: (e) {
        // Only log; do not break the chat flow
      });
    }

    // Add placeholder for AI response
    final aiMessageIndex = _messages.length;
    setState(() {
      _messages.add(ChatMessage(
        text: '',
        isUser: false,
        timestamp: DateTime.now(),
        isStreaming: true,
      ));
    });

    try {
      final request = http.Request('POST', Uri.parse(_apiUrl));
      request.headers['Content-Type'] = 'application/json';
      final accessToken = Supabase.instance.client.auth.currentSession?.accessToken;
      if (accessToken != null) {
        request.headers['Authorization'] = 'Bearer $accessToken';
      }

      // Build conversation history (exclude the placeholder AI message we just added)
      final history = <Map<String, String>>[];
      for (int i = 0; i < _messages.length - 1; i++) {
        final msg = _messages[i];
        if (msg.text.isNotEmpty) {
          history.add({
            'role': msg.isUser ? 'user' : 'assistant',
            'content': msg.text,
          });
        }
      }

      // For new conversations (no id yet), send history so BE can answer.
      // For existing conversations, let the backend load history from Supabase
      // using conversation_id to avoid sending long histories over HTTP.
      final useHistory = _conversationId == null;
      
      request.body = json.encode({
        'query': message,
        'history': useHistory ? history : <Map<String, String>>[],
        'conversation_id': _conversationId,
      });

      final streamedResponse = await request.send();

      if (streamedResponse.statusCode == 200) {
        String accumulatedText = '';

        await for (var chunk in streamedResponse.stream.transform(utf8.decoder)) {
          // Parse SSE format
          final lines = chunk.split('\n');
          for (var line in lines) {
              if (line.startsWith('data: ')) {
                final data = line.substring(6);
                if (data == '[DONE]') {
                  setState(() {
                    _messages[aiMessageIndex].isStreaming = false;
                    _isStreaming = false;
                  });

                  // Store full assistant message after streaming finishes
                  final fullText = accumulatedText;
                  if (_conversationId != null && fullText.trim().isNotEmpty) {
                    _conversationRepository
                        .createMessage(
                          conversationId: _conversationId!,
                          speaker: ConversationSpeaker.assistant,
                          content: fullText,
                        )
                        .then((_) {}, onError: (e) {
                      // Ignore persistence errors for now
                    });
                  }
              } else if (data.startsWith('[META]')) {
                // Parse metadata (time to first token)
                try {
                  final metaJson = data.substring(6);
                  final metadata = json.decode(metaJson);
                  if (metadata['ttft'] != null) {
                    setState(() {
                      _messages[aiMessageIndex].timeToFirstToken = metadata['ttft'];
                    });
                  }
                } catch (e) {
                  // Ignore metadata parsing errors
                }
              } else {
                // Unescape newlines from SSE format
                final unescapedData = data.replaceAll('\\n', '\n');
                accumulatedText += unescapedData;
                setState(() {
                  _messages[aiMessageIndex].text = accumulatedText;
                });
                _scrollToBottom();
              }
            }
          }
        }
      } else {
        setState(() {
          _messages[aiMessageIndex].text = 'Eroare: Nu am putut obține răspuns de la server.';
          _messages[aiMessageIndex].isStreaming = false;
          _isStreaming = false;
        });
      }
    } catch (e) {
      setState(() {
        _messages[aiMessageIndex].text = 'Eroare de conexiune: $e';
        _messages[aiMessageIndex].isStreaming = false;
        _isStreaming = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        ConversationSidebar(
          type: ConversationType.clarify,
          selectedConversation: _activeConversation,
          onConversationSelected: (conversation) {
            if (conversation == null) {
              setState(() {
                _activeConversation = null;
                _conversationId = null;
                _messages.clear();
                _isStreaming = false;
              });
            } else {
              _loadConversationHistory(conversation);
            }
          },
        ),
        Expanded(
          child: Column(
            children: [
              if (_isLoadingHistory)
                const LinearProgressIndicator(minHeight: 2),
              // Chat messages
              Expanded(
                child: _messages.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.help_outline,
                              size: 80,
                              color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Pune o întrebare despre ce nu ai înțeles!',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyLarge
                                  ?.copyWith(
                                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                                  ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(16),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          return _buildMessageBubble(_messages[index]);
                        },
                      ),
              ),
              // Input area
              Container(
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surface,
                  boxShadow: [
                    BoxShadow(
                      color: Theme.of(context).colorScheme.shadow.withOpacity(0.2),
                      blurRadius: 4,
                      offset: const Offset(0, -2),
                    ),
                  ],
                ),
                padding: const EdgeInsets.all(16),
                child: SafeArea(
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _messageController,
                          decoration: InputDecoration(
                            hintText: 'Scrie mesajul tău...',
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(24),
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 20,
                              vertical: 12,
                            ),
                          ),
                          maxLines: null,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => _sendMessage(),
                          enabled: !_isStreaming && !_isLoadingHistory,
                        ),
                      ),
                      const SizedBox(width: 8),
                      FloatingActionButton(
                        onPressed:
                            _isStreaming || _isLoadingHistory ? null : _sendMessage,
                        child: _isStreaming
                            ? SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Theme.of(context).colorScheme.onPrimary,
                                ),
                              )
                            : const Icon(Icons.send),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    final scheme = Theme.of(context).colorScheme;

    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Column(
        crossAxisAlignment: message.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Show time to first token above assistant messages
          if (!message.isUser && message.timeToFirstToken != null)
            Padding(
              padding: const EdgeInsets.only(left: 16, bottom: 4),
              child: Text(
                'Time to first token: ${message.timeToFirstToken!.toStringAsFixed(2)}s',
                style: TextStyle(
                  fontSize: 11,
                  color: scheme.onSurfaceVariant,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            decoration: BoxDecoration(
              color: message.isUser
                  ? scheme.primary
                  : scheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (message.isUser)
              // User messages: simple text
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Text(
                  message.text,
                  style: TextStyle(
                    color: message.isUser
                        ? scheme.onPrimary
                        : scheme.onSurface,
                    fontSize: 16,
                  ),
                ),
              )
            else
              // AI messages: markdown support
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: MarkdownBody(
                  data: message.text.isEmpty ? '_Typing..._' : message.text,
                  selectable: true,
                  shrinkWrap: true,
                  fitContent: true,
                  builders: {
                    'latex': LatexElementBuilder(),
                    'code': CustomCodeElementBuilder(),
                  },
                  inlineSyntaxes: [LatexInlineSyntax()],
                  styleSheet: MarkdownStyleSheet(
                    p: TextStyle(
                      color: scheme.onSurface,
                      fontSize: 16,
                      height: 1.5,
                    ),
                    strong: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                    ),
                    em: const TextStyle(
                      fontStyle: FontStyle.italic,
                    ),
                    code: TextStyle(
                      backgroundColor: scheme.surface,
                      color: scheme.onSurface,
                      fontFamily: 'monospace',
                      fontSize: 14,
                    ),
                    codeblockPadding: const EdgeInsets.all(8),
                    codeblockDecoration: BoxDecoration(
                      color: scheme.surface,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    blockquote: TextStyle(
                      color: scheme.onSurfaceVariant,
                      fontStyle: FontStyle.italic,
                    ),
                    blockquotePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    blockquoteDecoration: BoxDecoration(
                      color: scheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(4),
                      border: Border(
                        left: BorderSide(
                          color: scheme.outline,
                          width: 4,
                        ),
                      ),
                    ),
                    h1: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                      height: 1.5,
                    ),
                    h2: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                      height: 1.4,
                    ),
                    h3: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                      height: 1.3,
                    ),
                    listBullet: TextStyle(
                      color: scheme.onSurface,
                      fontSize: 16,
                    ),
                    listIndent: 24,
                    h1Padding: const EdgeInsets.only(top: 8, bottom: 4),
                    h2Padding: const EdgeInsets.only(top: 8, bottom: 4),
                    h3Padding: const EdgeInsets.only(top: 8, bottom: 4),
                  ),
                ),
              ),
            if (message.isStreaming)
              Padding(
                padding: const EdgeInsets.only(left: 16, right: 16, bottom: 12),
                child: SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: message.isUser
                        ? scheme.onPrimary
                        : scheme.onSurfaceVariant,
                  ),
                ),
              ),
          ],
        ),
      ),
      ],
      ),
    );
  }
}

// Guided Learning Tab - Interactive step-by-step mode
class GuidedLearningTab extends StatefulWidget {
  const GuidedLearningTab({super.key});

  @override
  State<GuidedLearningTab> createState() => _GuidedLearningTabState();
}

class _GuidedLearningTabState extends State<GuidedLearningTab> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isStreaming = false;

  final ConversationRepository _conversationRepository = ConversationRepository();
  Conversation? _activeConversation;
  int? _conversationId;
  bool _isLoadingHistory = false;

  String get _apiUrl => '${AppConfig.apiBaseUrl}/clarify/step-by-step-stream';

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _ensureConversationCreated(String firstUserMessage) async {
    if (_conversationId != null) return;

    final title = firstUserMessage.trim().isEmpty
        ? null
        : (firstUserMessage.trim().length > 80
            ? '${firstUserMessage.trim().substring(0, 80)}...'
            : firstUserMessage.trim());

    final conv = await _conversationRepository.createConversation(
      type: ConversationType.clarifySteps,
      title: title,
    );

    if (!mounted) return;
    setState(() {
      _activeConversation = conv;
      _conversationId = conv.id;
    });
  }

  Future<void> _loadConversationHistory(Conversation conversation) async {
    setState(() {
      _isLoadingHistory = true;
      _isStreaming = false;
    });

    try {
      final messages = await _conversationRepository.listMessages(
        conversationId: conversation.id,
      );

      if (!mounted) return;

      setState(() {
        _messages
          ..clear()
          ..addAll(
            messages.map(
              (m) => ChatMessage(
                text: m.content ?? '',
                isUser: m.speaker == ConversationSpeaker.user,
                timestamp: m.createdAt,
              ),
            ),
          );
        _activeConversation = conversation;
        _conversationId = conversation.id;
      });
      _scrollToBottom();
    } finally {
      if (!mounted) return;
      setState(() {
        _isLoadingHistory = false;
      });
    }
  }

  Future<void> _sendMessage() async {
    final message = _messageController.text.trim();
    if (message.isEmpty || _isStreaming) return;

    // Add user message
    setState(() {
      _messages.add(ChatMessage(
        text: message,
        isUser: true,
        timestamp: DateTime.now(),
      ));
      _isStreaming = true;
    });

    _messageController.clear();
    _scrollToBottom();

    // Ensure a conversation exists for this thread
    try {
      await _ensureConversationCreated(message);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Nu am putut crea conversația: $e')),
        );
      }
    }

    // Fire-and-forget: store the user message
    if (_conversationId != null) {
      _conversationRepository
          .createMessage(
            conversationId: _conversationId!,
            speaker: ConversationSpeaker.user,
            content: message,
          )
          .then((_) {}, onError: (e) {
        // Only log; do not break the chat flow
      });
    }

    // Add placeholder for AI response
    final aiMessageIndex = _messages.length;
    setState(() {
      _messages.add(ChatMessage(
        text: '',
        isUser: false,
        timestamp: DateTime.now(),
        isStreaming: true,
      ));
    });

    try {
      final request = http.Request('POST', Uri.parse(_apiUrl));
      request.headers['Content-Type'] = 'application/json';
      final accessToken = Supabase.instance.client.auth.currentSession?.accessToken;
      if (accessToken != null) {
        request.headers['Authorization'] = 'Bearer $accessToken';
      }

      // Build conversation history (exclude the placeholder AI message we just added)
      final history = <Map<String, String>>[];
      for (int i = 0; i < _messages.length - 1; i++) {
        final msg = _messages[i];
        if (msg.text.isNotEmpty) {
          history.add({
            'role': msg.isUser ? 'user' : 'assistant',
            'content': msg.text,
          });
        }
      }

      // For new conversations (no id yet), send history so BE can answer.
      // For existing conversations, let the backend load history from Supabase
      // using conversation_id to avoid sending long histories over HTTP.
      final useHistory = _conversationId == null;
      
      request.body = json.encode({
        'query': message,
        'history': useHistory ? history : <Map<String, String>>[],
        'conversation_id': _conversationId,
      });

      final streamedResponse = await request.send();

      if (streamedResponse.statusCode == 200) {
        String accumulatedText = '';

        await for (var chunk in streamedResponse.stream.transform(utf8.decoder)) {
          // Parse SSE format
          final lines = chunk.split('\n');
          for (var line in lines) {
              if (line.startsWith('data: ')) {
                final data = line.substring(6);
                if (data == '[DONE]') {
                  setState(() {
                    _messages[aiMessageIndex].isStreaming = false;
                    _isStreaming = false;
                  });

                  // Store full assistant message after streaming finishes
                  final fullText = accumulatedText;
                  if (_conversationId != null && fullText.trim().isNotEmpty) {
                    _conversationRepository
                        .createMessage(
                          conversationId: _conversationId!,
                          speaker: ConversationSpeaker.assistant,
                          content: fullText,
                        )
                        .then((_) {}, onError: (e) {
                      // Ignore persistence errors for now
                    });
                  }
              } else if (data.startsWith('[META]')) {
                // Parse metadata (time to first token)
                try {
                  final metaJson = data.substring(6);
                  final metadata = json.decode(metaJson);
                  if (metadata['ttft'] != null) {
                    setState(() {
                      _messages[aiMessageIndex].timeToFirstToken = metadata['ttft'];
                    });
                  }
                } catch (e) {
                  // Ignore metadata parsing errors
                }
              } else {
                // Unescape newlines from SSE format
                final unescapedData = data.replaceAll('\\n', '\n');
                accumulatedText += unescapedData;
                setState(() {
                  _messages[aiMessageIndex].text = accumulatedText;
                });
                _scrollToBottom();
              }
            }
          }
        }
      } else {
        setState(() {
          _messages[aiMessageIndex].text = 'Eroare: Nu am putut obține răspuns de la server.';
          _messages[aiMessageIndex].isStreaming = false;
          _isStreaming = false;
        });
      }
    } catch (e) {
      setState(() {
        _messages[aiMessageIndex].text = 'Eroare de conexiune: $e';
        _messages[aiMessageIndex].isStreaming = false;
        _isStreaming = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        ConversationSidebar(
          type: ConversationType.clarifySteps,
          selectedConversation: _activeConversation,
          onConversationSelected: (conversation) {
            if (conversation == null) {
              setState(() {
                _activeConversation = null;
                _conversationId = null;
                _messages.clear();
                _isStreaming = false;
              });
            } else {
              _loadConversationHistory(conversation);
            }
          },
        ),
        Expanded(
          child: Column(
            children: [
              if (_isLoadingHistory)
                const LinearProgressIndicator(minHeight: 2),
              // Chat messages
              Expanded(
                child: _messages.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.school_outlined,
                              size: 80,
                              color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
                            ),
                            const SizedBox(height: 16),
                            Padding(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 32),
                              child: Text(
                                'Pune o întrebare și te voi ghida pas cu pas să înțelegi conceptul!',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyLarge
                                    ?.copyWith(
                                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                                    ),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(16),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          return _buildMessageBubble(_messages[index]);
                        },
                      ),
              ),
              // Input area
              Container(
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surface,
                  boxShadow: [
                    BoxShadow(
                      color: Theme.of(context).colorScheme.shadow.withOpacity(0.2),
                      blurRadius: 4,
                      offset: const Offset(0, -2),
                    ),
                  ],
                ),
                padding: const EdgeInsets.all(16),
                child: SafeArea(
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _messageController,
                          decoration: InputDecoration(
                            hintText: 'Scrie mesajul tău...',
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(24),
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 20,
                              vertical: 12,
                            ),
                          ),
                          maxLines: null,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => _sendMessage(),
                          enabled: !_isStreaming && !_isLoadingHistory,
                        ),
                      ),
                      const SizedBox(width: 8),
                      FloatingActionButton(
                        onPressed:
                            _isStreaming || _isLoadingHistory ? null : _sendMessage,
                        child: _isStreaming
                            ? SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Theme.of(context).colorScheme.onPrimary,
                                ),
                              )
                            : const Icon(Icons.send),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    final scheme = Theme.of(context).colorScheme;

    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Column(
        crossAxisAlignment: message.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Show time to first token above assistant messages
          if (!message.isUser && message.timeToFirstToken != null)
            Padding(
              padding: const EdgeInsets.only(left: 16, bottom: 4),
              child: Text(
                'Time to first token: ${message.timeToFirstToken!.toStringAsFixed(2)}s',
                style: TextStyle(
                  fontSize: 11,
                  color: scheme.onSurfaceVariant,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            decoration: BoxDecoration(
              color: message.isUser
                  ? scheme.primary
                  : scheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (message.isUser)
              // User messages: simple text
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Text(
                  message.text,
                  style: TextStyle(
                    color: message.isUser
                        ? scheme.onPrimary
                        : scheme.onSurface,
                    fontSize: 16,
                  ),
                ),
              )
            else
              // AI messages: markdown support
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: MarkdownBody(
                  data: message.text.isEmpty ? '_Typing..._' : message.text,
                  selectable: true,
                  shrinkWrap: true,
                  fitContent: true,
                  builders: {
                    'latex': LatexElementBuilder(),
                    'code': CustomCodeElementBuilder(),
                  },
                  inlineSyntaxes: [LatexInlineSyntax()],
                  styleSheet: MarkdownStyleSheet(
                    p: TextStyle(
                      color: scheme.onSurface,
                      fontSize: 16,
                      height: 1.5,
                    ),
                    strong: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                    ),
                    em: const TextStyle(
                      fontStyle: FontStyle.italic,
                    ),
                    code: TextStyle(
                      backgroundColor: scheme.surface,
                      color: scheme.onSurface,
                      fontFamily: 'monospace',
                      fontSize: 14,
                    ),
                    codeblockPadding: const EdgeInsets.all(8),
                    codeblockDecoration: BoxDecoration(
                      color: scheme.surface,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    blockquote: TextStyle(
                      color: scheme.onSurfaceVariant,
                      fontStyle: FontStyle.italic,
                    ),
                    blockquotePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    blockquoteDecoration: BoxDecoration(
                      color: scheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(4),
                      border: Border(
                        left: BorderSide(
                          color: scheme.outline,
                          width: 4,
                        ),
                      ),
                    ),
                    h1: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                      height: 1.5,
                    ),
                    h2: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                      height: 1.4,
                    ),
                    h3: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                      height: 1.3,
                    ),
                    listBullet: TextStyle(
                      color: scheme.onSurface,
                      fontSize: 16,
                    ),
                    listIndent: 24,
                    h1Padding: const EdgeInsets.only(top: 8, bottom: 4),
                    h2Padding: const EdgeInsets.only(top: 8, bottom: 4),
                    h3Padding: const EdgeInsets.only(top: 8, bottom: 4),
                  ),
                ),
              ),
            if (message.isStreaming)
              Padding(
                padding: const EdgeInsets.only(left: 16, right: 16, bottom: 12),
                child: SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: message.isUser
                        ? scheme.onPrimary
                        : scheme.onSurfaceVariant,
                  ),
                ),
              ),
          ],
        ),
      ),
      ],
      ),
    );
  }
}

class ChatMessage {
  String text;
  final bool isUser;
  final DateTime timestamp;
  bool isStreaming;
  double? timeToFirstToken; // Time in seconds

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.isStreaming = false,
    this.timeToFirstToken,
  });
}

// LaTeX inline syntax for parsing $...$ or $$...$$ 
class LatexInlineSyntax extends md.InlineSyntax {
  LatexInlineSyntax() : super(r'\$\$(.+?)\$\$|\$(.+?)\$');

  @override
  bool onMatch(md.InlineParser parser, Match match) {
    final latex = match.group(1) ?? match.group(2);
    if (latex == null) return false;

    final isBlock = match.group(0)!.startsWith(r'$$');
    final element = md.Element.text('latex', latex);
    element.attributes['display'] = isBlock ? 'block' : 'inline';
    parser.addNode(element);
    return true;
  }
}

// LaTeX element builder for rendering
class LatexElementBuilder extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final latex = element.textContent;
    final isBlock = element.attributes['display'] == 'block';

    return Builder(
      builder: (context) {
        final scheme = Theme.of(context).colorScheme;

        try {
          return Padding(
            padding: isBlock
                ? const EdgeInsets.symmetric(vertical: 8)
                : EdgeInsets.zero,
            child: Math.tex(
              latex,
              mathStyle: isBlock ? MathStyle.display : MathStyle.text,
              textStyle: preferredStyle?.copyWith(fontSize: isBlock ? 18 : 16),
              options: MathOptions(
                fontSize: isBlock ? 18 : 16,
                color: scheme.onSurface,
              ),
            ),
          );
        } catch (e) {
          // If LaTeX parsing fails, display the raw text
          return Text(
            isBlock ? '\$\$$latex\$\$' : '\$$latex\$',
            style: TextStyle(
              color: scheme.error,
              fontFamily: 'monospace',
              fontSize: 14,
            ),
          );
        }
      },
    );
  }
}

// Custom code element builder that handles both regular code and graphs
class CustomCodeElementBuilder extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final language = element.attributes['class']?.replaceFirst('language-', '') ?? '';
    final code = element.textContent;

    // Check if this is a graph code block
    if (language == 'graph') {
      return _buildGraph(code);
    }

    // Default code block rendering with theme support
    return Builder(
      builder: (context) {
        final scheme = Theme.of(context).colorScheme;
        return Container(
          padding: const EdgeInsets.all(12),
          margin: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: scheme.surface,
            borderRadius: BorderRadius.circular(8),
          ),
          child: SelectableText(
            code,
            style: TextStyle(
              fontFamily: 'monospace',
              fontSize: 14,
              color: scheme.onSurface,
            ),
          ),
        );
      },
    );
  }

  Widget _buildGraph(String content) {
    // Parse the graph definition - collect ALL functions, not just unique keys
    final params = <String, String>{};
    final functions = <String>[];
    final lines = content.trim().split('\n');
    
    for (final line in lines) {
      final colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        final key = line.substring(0, colonIndex).trim();
        final value = line.substring(colonIndex + 1).trim();
        
        // Collect all function values (handle duplicate 'function:' keys)
        if (key == 'function' && value.isNotEmpty) {
          functions.add(value);
        } else if (key.startsWith('function') && value.isNotEmpty) {
          // Handle function1, function2, etc. - extract number for ordering
          final numMatch = RegExp(r'function(\d+)').firstMatch(key);
          if (numMatch != null) {
            final index = int.parse(numMatch.group(1)!);
            // Ensure list is large enough
            while (functions.length < index) {
              functions.add('');
            }
            // Insert at correct position (1-indexed)
            if (index > 0) {
              functions[index - 1] = value;
            }
          }
        } else {
          // Store other parameters normally
          params[key] = value;
        }
      }
    }

    // Remove empty function entries
    functions.removeWhere((f) => f.isEmpty);

    if (functions.isEmpty) {
      return Builder(
        builder: (context) {
          final scheme = Theme.of(context).colorScheme;
          return Container(
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              color: scheme.errorContainer,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'Invalid graph: missing function parameter',
              style: TextStyle(color: scheme.error),
            ),
          );
        },
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: FunctionGraphWidget(
        functions: functions,
        xMin: double.tryParse(params['xMin'] ?? '-5') ?? -5,
        xMax: double.tryParse(params['xMax'] ?? '5') ?? 5,
        yMin: double.tryParse(params['yMin'] ?? '-5') ?? -5,
        yMax: double.tryParse(params['yMax'] ?? '5') ?? 5,
        title: params['title'],
      ),
    );
  }
}

// Widget to render function graphs
class FunctionGraphWidget extends StatelessWidget {
  final List<String> functions;
  final double xMin;
  final double xMax;
  final double yMin;
  final double yMax;
  final String? title;

  const FunctionGraphWidget({
    super.key,
    required this.functions,
    required this.xMin,
    required this.xMax,
    required this.yMin,
    required this.yMax,
    this.title,
  });

  List<FlSpot> _generatePoints(String functionStr) {
    final points = <FlSpot>[];
    
    try {
      // Parse the function string (e.g., "f(x)=x^2" or just "x^2")
      String expression = functionStr;
      if (expression.contains('=')) {
        expression = expression.split('=').last.trim();
      }
      
      // Replace common patterns for math_expressions parser
      expression = expression
          .replaceAll('sin', 'sin')
          .replaceAll('cos', 'cos')
          .replaceAll('tan', 'tan')
          .replaceAll('sqrt', 'sqrt')
          .replaceAll('ln', 'ln')
          .replaceAll('log', 'log');

      final parser = Parser();
      final exp = parser.parse(expression);
      final variable = Variable('x');
      final cm = ContextModel();

      // Generate points
      final step = (xMax - xMin) / 200; // 200 points for smooth curve
      
      for (double x = xMin; x <= xMax; x += step) {
        try {
          cm.bindVariable(variable, Number(x));
          final y = exp.evaluate(EvaluationType.REAL, cm);
          
          if (y.isFinite && y >= yMin && y <= yMax) {
            points.add(FlSpot(x, y));
          }
        } catch (_) {
          // Skip invalid points
        }
      }
    } catch (e) {
      // If parsing fails, return empty list
      return [];
    }

    return points;
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    // Define colors for multiple functions
    final lineColors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
    ];

    // Generate points for each function
    final allLineData = <LineChartBarData>[];
    final functionLabels = <String>[];
    
    for (int i = 0; i < functions.length; i++) {
      final points = _generatePoints(functions[i]);
      if (points.isNotEmpty) {
        allLineData.add(
          LineChartBarData(
            spots: points,
            isCurved: true,
            color: lineColors[i % lineColors.length],
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(show: false),
          ),
        );
        functionLabels.add(functions[i]);
      }
    }

    if (allLineData.isEmpty) {
      return Container(
        height: 250,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: scheme.errorContainer,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            'Could not render graph for: ${functions.join(", ")}',
            style: TextStyle(color: scheme.error),
          ),
        ),
      );
    }

    return Container(
      height: 250,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: scheme.outlineVariant,
        ),
      ),
      child: Column(
        children: [
          if (title != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                title!,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: scheme.onSurface,
                ),
              ),
            ),
          Expanded(
            child: LineChart(
              LineChartData(
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: true,
                  horizontalInterval: (yMax - yMin) / 5,
                  verticalInterval: (xMax - xMin) / 5,
                  getDrawingHorizontalLine: (value) {
                    return FlLine(
                      color: scheme.outlineVariant,
                      strokeWidth: 1,
                    );
                  },
                  getDrawingVerticalLine: (value) {
                    return FlLine(
                      color: scheme.outlineVariant,
                      strokeWidth: 1,
                    );
                  },
                ),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 40,
                      getTitlesWidget: (value, meta) {
                        return Text(
                          value.toStringAsFixed(1),
                          style: TextStyle(
                            fontSize: 10,
                            color: scheme.onSurface,
                          ),
                        );
                      },
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      getTitlesWidget: (value, meta) {
                        return Text(
                          value.toStringAsFixed(1),
                          style: TextStyle(
                            fontSize: 10,
                            color: scheme.onSurface,
                          ),
                        );
                      },
                    ),
                  ),
                  rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                ),
                borderData: FlBorderData(
                  show: true,
                  border: Border.all(
                    color: scheme.outline,
                  ),
                ),
                minX: xMin,
                maxX: xMax,
                minY: yMin,
                maxY: yMax,
                lineBarsData: allLineData,
              ),
            ),
          ),
          // Show legend with function labels and colors
          if (functionLabels.length > 1)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Wrap(
                spacing: 12,
                runSpacing: 4,
                children: List.generate(functionLabels.length, (i) {
                  return Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 16,
                        height: 2,
                        color: lineColors[i % lineColors.length],
                      ),
                      const SizedBox(width: 4),
                      Text(
                        functionLabels[i],
                        style: TextStyle(
                          fontSize: 11,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  );
                }),
              ),
            )
          else
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                functionLabels.first,
                style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
