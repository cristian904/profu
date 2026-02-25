import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:fl_chart/fl_chart.dart';
import 'package:math_expressions/math_expressions.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:async' show Timer, TimeoutException;

import '../config/app_config.dart';
import '../models/conversation_models.dart';
import '../services/conversation_repository.dart';
import '../widgets/conversation_sidebar.dart';
import '../widgets/profu_drawer.dart';

class SolveProblemPage extends StatefulWidget {
  const SolveProblemPage({super.key});

  @override
  State<SolveProblemPage> createState() => _SolveProblemPageState();
}

class _SolveProblemPageState extends State<SolveProblemPage> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isStreaming = false;
  bool _isLoadingHistory = false;
  bool _isLoadingSimilarProblems = false;
  String? _problemText;
  File? _selectedImage; // For mobile
  Uint8List? _selectedImageBytes; // For web
  String? _selectedImageName;

  final ConversationRepository _conversationRepository = ConversationRepository();
  Conversation? _activeConversation;
  int? _conversationId;

  String get _apiUrl => '${AppConfig.apiBaseUrl}/solve-problem';
  String get _uploadUrl => '${AppConfig.apiBaseUrl}/solve-problem/upload';

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

    final baseText = (_problemText?.trim().isNotEmpty ?? false)
        ? _problemText!.trim()
        : firstUserMessage.trim();

    final title = baseText.isEmpty
        ? null
        : (baseText.length > 80 ? '${baseText.substring(0, 80)}...' : baseText);

    final conv = await _conversationRepository.createConversation(
      type: ConversationType.problemSolving,
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

  Future<void> _pickImage() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.image,
        allowMultiple: false,
      );

      if (result != null && result.files.single.size > 0) {
        final file = result.files.single;
        
        if (kIsWeb) {
          // On web, use bytes
          if (file.bytes != null) {
            setState(() {
              _selectedImageBytes = file.bytes;
              _selectedImageName = file.name;
            });
            // Upload image and perform OCR
            await _uploadImageBytes(_selectedImageBytes!, _selectedImageName!);
          }
        } else {
          // On mobile, use path
          if (file.path != null) {
            setState(() {
              _selectedImage = File(file.path!);
              _selectedImageName = file.name;
            });
            // Upload image and perform OCR
            await _uploadImage(_selectedImage!);
          }
        }
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare la selectarea imaginii: $e')),
      );
    }
  }

  Future<void> _uploadImage(File imageFile) async {
    debugPrint('[FE UPLOAD] ===== Starting image upload =====');
    debugPrint('[FE UPLOAD] File path: ${imageFile.path}');
    
    try {
      setState(() {
        _isStreaming = true;
      });

      // Create multipart request
      debugPrint('[FE UPLOAD] Creating multipart request to: $_uploadUrl');
      var request = http.MultipartRequest('POST', Uri.parse(_uploadUrl));
      request.files.add(
        await http.MultipartFile.fromPath('file', imageFile.path),
      );

      // Send request
      debugPrint('[FE UPLOAD] Sending request...');
      var streamedResponse = await request.send();
      debugPrint('[FE UPLOAD] Response status: ${streamedResponse.statusCode}');
      var response = await http.Response.fromStream(streamedResponse);
      debugPrint('[FE UPLOAD] Response body length: ${response.body.length}');

      await _handleUploadResponse(response);
    } catch (e) {
      setState(() {
        _isStreaming = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare: $e')),
      );
    }
  }

  Future<void> _uploadImageBytes(Uint8List imageBytes, String fileName) async {
    debugPrint('[FE UPLOAD] ===== Starting image upload (bytes) =====');
    debugPrint('[FE UPLOAD] File name: $fileName');
    debugPrint('[FE UPLOAD] Image bytes: ${imageBytes.length}');
    
    try {
      setState(() {
        _isStreaming = true;
      });

      // Determine content type from file extension
      String contentType = 'image/jpeg'; // default
      final extension = fileName.toLowerCase().split('.').last;
      switch (extension) {
        case 'png':
          contentType = 'image/png';
          break;
        case 'jpg':
        case 'jpeg':
          contentType = 'image/jpeg';
          break;
        case 'gif':
          contentType = 'image/gif';
          break;
        case 'webp':
          contentType = 'image/webp';
          break;
        case 'bmp':
          contentType = 'image/bmp';
          break;
      }
      debugPrint('[FE UPLOAD] Content type: $contentType');

      // Create multipart request
      debugPrint('[FE UPLOAD] Creating multipart request to: $_uploadUrl');
      var request = http.MultipartRequest('POST', Uri.parse(_uploadUrl));
      
      // Add file - content-type will be inferred from filename by the http package
      // The backend will also check file extension if content-type is missing
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          imageBytes,
          filename: fileName,
        ),
      );

      // Send request
      debugPrint('[FE UPLOAD] Sending request...');
      var streamedResponse = await request.send();
      debugPrint('[FE UPLOAD] Response status: ${streamedResponse.statusCode}');
      var response = await http.Response.fromStream(streamedResponse);
      debugPrint('[FE UPLOAD] Response body length: ${response.body.length}');

      await _handleUploadResponse(response);
    } catch (e) {
      setState(() {
        _isStreaming = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare: $e')),
      );
    }
  }

  Future<void> _handleUploadResponse(http.Response response) async {
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      setState(() {
        _problemText = data['problem_text'];
        _isStreaming = false;
      });

      // Add the initial AI message directly in the UI (no question; two buttons below)
      final problemText = data['problem_text'] ?? '';
      String initialMessage;
      if (problemText.isNotEmpty) {
        initialMessage = "Pare o problemă interesantă!\n\n**Problema:**\n$problemText";
      } else {
        initialMessage = "Pare o problemă interesantă!";
      }

      // Ensure the conversation exists and store the first assistant message
      try {
        await _ensureConversationCreated(initialMessage);
        if (_conversationId != null && initialMessage.trim().isNotEmpty) {
          _conversationRepository
              .createMessage(
                conversationId: _conversationId!,
                speaker: ConversationSpeaker.assistant,
                content: initialMessage,
              )
              .then((_) {}, onError: (e) {
            // Ignore persistence errors for now
          });
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Nu am putut salva conversația: $e')),
          );
        }
      }

      setState(() {
        _messages.add(ChatMessage(
          text: initialMessage,
          isUser: false,
          timestamp: DateTime.now(),
          isStreaming: false,
        ));
      });

      _scrollToBottom();
    } else {
      setState(() {
        _isStreaming = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare la procesarea imaginii: ${response.statusCode}')),
      );
    }
  }


  Future<void> _sendMessage(String message) async {
    if (_isStreaming || _problemText == null) return;
    if (message.isEmpty) return;

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
      final request = http.Request('POST', Uri.parse('$_apiUrl/stream'));
      request.headers['Content-Type'] = 'application/json';

      // Build conversation history
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

      request.body = json.encode({
        'query': message,
        'problem_text': _problemText,
        'history': history,
      });

      final streamedResponse = await request.send();

      if (streamedResponse.statusCode == 200) {
        String accumulatedText = '';
        bool shouldStop = false;
        Timer? timeoutTimer;

        try {
          // Set a timeout to stop streaming after 30 seconds (safety net)
          timeoutTimer = Timer(const Duration(seconds: 30), () {
            if (mounted && aiMessageIndex < _messages.length) {
              setState(() {
                _messages[aiMessageIndex].isStreaming = false;
                _isStreaming = false;
              });
            }
          });

          await for (var chunk in streamedResponse.stream
              .transform(utf8.decoder)
              .timeout(const Duration(seconds: 30))) {
            if (shouldStop) break;
            
            // Parse SSE format
            final lines = chunk.split('\n');
            for (var line in lines) {
              if (shouldStop) break;
              
              if (line.startsWith('data: ')) {
                final data = line.substring(6);
                
                if (data == '[DONE]') {
                  shouldStop = true;
                  timeoutTimer.cancel();
                  if (mounted) {
                    // Modify properties directly (same as working clarify_chat_page.dart)
                    if (aiMessageIndex < _messages.length) {
                      setState(() {
                        _messages[aiMessageIndex].isStreaming = false;
                        _isStreaming = false;
                      });

                      // Store assistant message when streaming ends
                      final fullText = accumulatedText;
                      if (_conversationId != null &&
                          fullText.trim().isNotEmpty) {
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
                    } else {
                      setState(() {
                        _isStreaming = false;
                      });
                    }
                  }
                  break;
                } else if (data.startsWith('[META]')) {
                  // Parse metadata (time to first token)
                  try {
                    final metaJson = data.substring(6);
                    final metadata = json.decode(metaJson);
                    if (metadata['ttft'] != null && mounted && aiMessageIndex < _messages.length) {
                      setState(() {
                        _messages[aiMessageIndex].timeToFirstToken = metadata['ttft'];
                      });
                    }
                  } catch (e) {
                    // Ignore metadata parsing errors
                  }
                } else if (data.isNotEmpty) {
                  // Unescape newlines from SSE format
                  final unescapedData = data.replaceAll('\\n', '\n');
                  accumulatedText += unescapedData;
                  if (mounted && aiMessageIndex < _messages.length) {
                    setState(() {
                      _messages[aiMessageIndex].text = accumulatedText;
                    });
                    _scrollToBottom();
                  }
                }
              }
            }
            if (shouldStop) break;
          }
          
          timeoutTimer.cancel();
        } on TimeoutException {
          timeoutTimer?.cancel();
        } catch (e) {
          debugPrint('[FE STREAM] ❌ Error reading stream: $e');
          if (timeoutTimer != null) {
            timeoutTimer.cancel();
          }
        } finally {
          // Always stop streaming when stream ends, regardless of [DONE] signal
          if (mounted) {
            if (aiMessageIndex < _messages.length) {
              // Modify properties directly (same as working clarify_chat_page.dart)
              setState(() {
                _messages[aiMessageIndex].isStreaming = false;
                _isStreaming = false;
              });
            } else {
              setState(() {
                _isStreaming = false;
              });
            }
          }
        }
      } else {
        if (aiMessageIndex < _messages.length) {
          setState(() {
            _messages[aiMessageIndex].text = 'Eroare: Nu am putut obține răspuns de la server.';
            _messages[aiMessageIndex].isStreaming = false;
            _isStreaming = false;
          });
        } else {
          setState(() {
            _isStreaming = false;
          });
        }
      }
    } catch (e) {
      if (aiMessageIndex < _messages.length) {
        setState(() {
          _messages[aiMessageIndex].text = 'Eroare de conexiune: $e';
          _messages[aiMessageIndex].isStreaming = false;
          _isStreaming = false;
        });
      } else {
        setState(() {
          _isStreaming = false;
        });
      }
    }
  }

  Future<void> _requestSimilarProblems() async {
    if (_problemText == null || _problemText!.trim().isEmpty) return;
    if (_isLoadingSimilarProblems || _isStreaming) return;

    setState(() {
      _isLoadingSimilarProblems = true;
    });

    try {
      final request = http.Request(
        'POST',
        Uri.parse('$_apiUrl/suggest-problem'),
      );
      request.headers['Content-Type'] = 'application/json';
      request.body = json.encode({'problem_text': _problemText});

      final response = await request.send();
      final body = await response.stream.transform(utf8.decoder).join();

      if (!mounted) return;

      if (response.statusCode == 200) {
        final data = json.decode(body) as Map<String, dynamic>;
        final message = data['message'] as String? ?? 'Nu am găsit probleme similare.';
        final problemsList = data['problems'] as List<dynamic>? ?? [];
        final statements = problemsList
            .map((e) => (e as Map<String, dynamic>)['statement'] as String? ?? '')
            .toList();

        setState(() {
          _isLoadingSimilarProblems = false;
          _messages.add(ChatMessage(
            text: message,
            isUser: false,
            timestamp: DateTime.now(),
            isStreaming: false,
            suggestedProblems: statements.isNotEmpty ? statements : null,
          ));
        });

        if (_conversationId != null && message.trim().isNotEmpty) {
          _conversationRepository
              .createMessage(
                conversationId: _conversationId!,
                speaker: ConversationSpeaker.assistant,
                content: message,
              )
              .then((_) {}, onError: (_) {});
        }
        _scrollToBottom();
      } else {
        setState(() {
          _isLoadingSimilarProblems = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Eroare la sugestii: ${response.statusCode}')),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoadingSimilarProblems = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Eroare: $e')),
        );
      }
    }
  }

  void _onWantToSolve() {
    if (_isStreaming || _problemText == null || _problemText!.trim().isEmpty) return;

    setState(() {
      _messages.add(ChatMessage(
        text: 'Vreau să o rezolv',
        isUser: true,
        timestamp: DateTime.now(),
      ));
      _messages.add(ChatMessage(
        text: 'Bună alegere. Vrei o rezolvare completă sau un hint?',
        isUser: false,
        timestamp: DateTime.now(),
        isStreaming: false,
        solutionChoiceButtons: ['Rezolvare completă', 'Hint'],
      ));
    });

    if (_conversationId != null) {
      _conversationRepository
          .createMessage(
            conversationId: _conversationId!,
            speaker: ConversationSpeaker.user,
            content: 'Vreau să o rezolv',
          )
          .then((_) {}, onError: (_) {});
      _conversationRepository
          .createMessage(
            conversationId: _conversationId!,
            speaker: ConversationSpeaker.assistant,
            content: 'Bună alegere. Vrei o rezolvare completă sau un hint?',
          )
          .then((_) {}, onError: (_) {});
    }
    _scrollToBottom();
  }

  void _selectSuggestedProblem(String statement) {
    if (statement.trim().isEmpty || _isStreaming) return;

    setState(() {
      _problemText = statement;
      _messages.add(ChatMessage(
        text: 'Vreau să rezolv această problemă',
        isUser: true,
        timestamp: DateTime.now(),
      ));
      final problemPreview = statement.length > 150
          ? '${statement.substring(0, 150)}...'
          : statement;
      _messages.add(ChatMessage(
        text: 'Am înțeles că vrei să rezolvi problema „$problemPreview”. Vrei o rezolvare completă sau un hint?',
        isUser: false,
        timestamp: DateTime.now(),
        isStreaming: false,
        solutionChoiceButtons: ['Rezolvare completă', 'Hint'],
      ));
    });

    if (_conversationId != null) {
      _conversationRepository
          .createMessage(
            conversationId: _conversationId!,
            speaker: ConversationSpeaker.user,
            content: 'Vreau să rezolv această problemă',
          )
          .then((_) {}, onError: (_) {});
      final problemPreview = statement.length > 150
          ? '${statement.substring(0, 150)}...'
          : statement;
      final aiText = 'Am înțeles că vrei să rezolvi problema „$problemPreview”. Vrei o rezolvare completă sau un hint?';
      _conversationRepository
          .createMessage(
            conversationId: _conversationId!,
            speaker: ConversationSpeaker.assistant,
            content: aiText,
          )
          .then((_) {}, onError: (_) {});
    }
    _scrollToBottom();
  }

  void _sendSolutionChoice(String choice) {
    if (_problemText == null || _problemText!.trim().isEmpty || _isStreaming) return;

    setState(() {
      _messages.add(ChatMessage(
        text: choice,
        isUser: true,
        timestamp: DateTime.now(),
      ));
      _isStreaming = true;
    });

    if (_conversationId != null) {
      _conversationRepository
          .createMessage(
            conversationId: _conversationId!,
            speaker: ConversationSpeaker.user,
            content: choice,
          )
          .then((_) {}, onError: (_) {});
    }

    final aiMessageIndex = _messages.length;
    setState(() {
      _messages.add(ChatMessage(
        text: '',
        isUser: false,
        timestamp: DateTime.now(),
        isStreaming: true,
      ));
    });
    _scrollToBottom();

    _streamSolutionWithQuery(choice, _problemText!, aiMessageIndex);
  }

  Future<void> _streamSolutionWithQuery(
    String query,
    String problemText,
    int aiMessageIndex,
  ) async {
    Timer? timeoutTimer;
    try {
      final request = http.Request('POST', Uri.parse('$_apiUrl/stream'));
      request.headers['Content-Type'] = 'application/json';
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
      request.body = json.encode({
        'query': query,
        'problem_text': problemText,
        'history': history,
      });

      final streamedResponse = await request.send();
      if (streamedResponse.statusCode != 200) {
        if (mounted && aiMessageIndex < _messages.length) {
          setState(() {
            _messages[aiMessageIndex].text =
                'Eroare: Nu am putut obține răspuns de la server.';
            _messages[aiMessageIndex].isStreaming = false;
            _isStreaming = false;
          });
        } else {
          setState(() => _isStreaming = false);
        }
        return;
      }

      String accumulatedText = '';
      bool shouldStop = false;
      timeoutTimer = Timer(const Duration(seconds: 30), () {
        if (mounted && aiMessageIndex < _messages.length) {
          setState(() {
            _messages[aiMessageIndex].isStreaming = false;
            _isStreaming = false;
          });
        }
      });

      await for (var chunk in streamedResponse.stream
          .transform(utf8.decoder)
          .timeout(const Duration(seconds: 30))) {
        if (shouldStop) break;
        final lines = chunk.split('\n');
        for (var line in lines) {
          if (shouldStop) break;
          if (line.startsWith('data: ')) {
            final data = line.substring(6);
            if (data == '[DONE]') {
              shouldStop = true;
              timeoutTimer.cancel();
              if (mounted && aiMessageIndex < _messages.length) {
                setState(() {
                  _messages[aiMessageIndex].isStreaming = false;
                  _isStreaming = false;
                });
                final fullText = accumulatedText;
                if (_conversationId != null && fullText.trim().isNotEmpty) {
                  _conversationRepository
                      .createMessage(
                        conversationId: _conversationId!,
                        speaker: ConversationSpeaker.assistant,
                        content: fullText,
                      )
                      .then((_) {}, onError: (_) {});
                }
              } else {
                setState(() => _isStreaming = false);
              }
              break;
            } else if (data.startsWith('[META]')) {
              try {
                final metaJson = data.substring(6);
                final metadata = json.decode(metaJson);
                if (metadata['ttft'] != null &&
                    mounted &&
                    aiMessageIndex < _messages.length) {
                  setState(() {
                    _messages[aiMessageIndex].timeToFirstToken =
                        (metadata['ttft'] as num).toDouble();
                  });
                }
              } catch (_) {}
            } else if (data.isNotEmpty) {
              final unescapedData = data.replaceAll('\\n', '\n');
              accumulatedText += unescapedData;
              if (mounted && aiMessageIndex < _messages.length) {
                setState(() {
                  _messages[aiMessageIndex].text = accumulatedText;
                });
                _scrollToBottom();
              }
            }
          }
        }
        if (shouldStop) break;
      }
      timeoutTimer.cancel();
    } on TimeoutException {
      timeoutTimer?.cancel();
    } catch (e) {
      timeoutTimer?.cancel();
      if (mounted && aiMessageIndex < _messages.length) {
        setState(() {
          _messages[aiMessageIndex].text = 'Eroare de conexiune: $e';
          _messages[aiMessageIndex].isStreaming = false;
          _isStreaming = false;
        });
      } else if (mounted) {
        setState(() => _isStreaming = false);
      }
    } finally {
      if (mounted && aiMessageIndex < _messages.length) {
        setState(() {
          _messages[aiMessageIndex].isStreaming = false;
          _isStreaming = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vreau să rezolv o problemă'),
        centerTitle: true,
      ),
      drawer: const ProfuDrawer(),
      body: Row(
        children: [
          ConversationSidebar(
            type: ConversationType.problemSolving,
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
                  child: _messages.isEmpty &&
                          _selectedImage == null &&
                          _selectedImageBytes == null
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.image_outlined,
                                size: 80,
                                color: Theme.of(context)
                                    .colorScheme
                                    .primary
                                    .withOpacity(0.5),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Încarcă o poză cu problema pe care vrei să o rezolvi!',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyLarge
                                    ?.copyWith(
                                      color: Theme.of(context)
                                          .colorScheme
                                          .onSurfaceVariant,
                                    ),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 24),
                              ElevatedButton.icon(
                                onPressed: _pickImage,
                                icon: const Icon(Icons.upload_file),
                                label: const Text('Încarcă imagine'),
                                style: ElevatedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 24,
                                    vertical: 12,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(16),
                          itemCount: _messages.length +
                              ((_selectedImage != null ||
                                      _selectedImageBytes != null)
                                  ? 1
                                  : 0),
                          itemBuilder: (context, index) {
                            // Show image preview at the beginning
                            if (index == 0 &&
                                (_selectedImage != null ||
                                    _selectedImageBytes != null)) {
                              return Container(
                                margin: const EdgeInsets.only(bottom: 12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Imaginea problemei:',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Theme.of(context)
                                            .colorScheme
                                            .onSurfaceVariant,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(8),
                                      child: kIsWeb && _selectedImageBytes != null
                                          ? Image.memory(
                                              _selectedImageBytes!,
                                              width: double.infinity,
                                              height: 200,
                                              fit: BoxFit.contain,
                                            )
                                          : _selectedImage != null
                                              ? Image.file(
                                                  _selectedImage!,
                                                  width: double.infinity,
                                                  height: 200,
                                                  fit: BoxFit.contain,
                                                )
                                              : const SizedBox.shrink(),
                                    ),
                                  ],
                                ),
                              );
                            }

                            // Adjust index for messages
                            final hasImage = _selectedImage != null ||
                                _selectedImageBytes != null;
                            final messageIndex = hasImage ? index - 1 : index;
                            if (messageIndex < 0 ||
                                messageIndex >= _messages.length) {
                              return const SizedBox.shrink();
                            }

                            int? firstAiIndex;
                            for (int i = 0; i < _messages.length; i++) {
                              if (!_messages[i].isUser) {
                                firstAiIndex = i;
                                break;
                              }
                            }
                            final isFirstAiMessage =
                                firstAiIndex != null && messageIndex == firstAiIndex;

                            return _buildMessageBubble(
                              _messages[messageIndex],
                              isFirstAiMessage: isFirstAiMessage,
                              key: ValueKey(
                                'msg_${messageIndex}_${_messages[messageIndex].timestamp.millisecondsSinceEpoch}_${_messages[messageIndex].isStreaming}',
                              ),
                            );
                          },
                        ),
                ),
                // Input area
                Container(
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface,
                    boxShadow: [
                      BoxShadow(
                        color: Theme.of(context)
                            .colorScheme
                            .shadow
                            .withOpacity(0.2),
                        blurRadius: 4,
                        offset: const Offset(0, -2),
                      ),
                    ],
                  ),
                  padding: const EdgeInsets.all(16),
                  child: SafeArea(
                    child: Row(
                      children: [
                        // Image upload button (only show if no image uploaded yet)
                        if (_selectedImage == null &&
                            _selectedImageBytes == null)
                          IconButton(
                            onPressed:
                                _isStreaming || _isLoadingHistory ? null : _pickImage,
                            icon: const Icon(Icons.image_outlined),
                            tooltip: 'Încarcă imagine',
                          ),
                        Expanded(
                          child: TextField(
                            controller: _messageController,
                            decoration: InputDecoration(
                              hintText: _problemText == null
                                  ? 'Încarcă mai întâi o imagine...'
                                  : 'Scrie mesajul tău...',
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
                            onSubmitted: (_) =>
                                _sendMessage(_messageController.text),
                            enabled: !_isStreaming &&
                                _problemText != null &&
                                !_isLoadingHistory,
                          ),
                        ),
                        const SizedBox(width: 8),
                        FloatingActionButton(
                          onPressed: _isStreaming ||
                                  _problemText == null ||
                                  _isLoadingHistory
                              ? null
                              : () => _sendMessage(_messageController.text),
                          child: _isStreaming
                              ? SizedBox(
                                  width: 24,
                                  height: 24,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onPrimary,
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
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage message,
      {bool isFirstAiMessage = false, Key? key}) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;

    return KeyedSubtree(
      key: key,
      child: Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Column(
        crossAxisAlignment:
            message.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
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
                        blockquotePadding:
                            const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
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
          // Two buttons under first AI message: similar problems + want to solve
          if (isFirstAiMessage &&
              !message.isUser &&
              !message.isStreaming &&
              _problemText != null &&
              _problemText!.trim().isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: 0, bottom: 10),
              child: Wrap(
                spacing: 10,
                runSpacing: 8,
                children: [
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: _isLoadingSimilarProblems || _isStreaming
                          ? null
                          : _requestSimilarProblems,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: Colors.cyan.shade400.withOpacity(0.9),
                            width: 1.8,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.cyan.withOpacity(0.15),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                          gradient: LinearGradient(
                            colors: [
                              Colors.cyan.shade900.withOpacity(0.25),
                              Colors.cyan.shade700.withOpacity(0.12),
                            ],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (_isLoadingSimilarProblems)
                              const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            else
                              Icon(Icons.auto_awesome, size: 18, color: Colors.cyan.shade300),
                            const SizedBox(width: 10),
                            Text(
                              _isLoadingSimilarProblems ? 'Se încarcă...' : 'vreau probleme similare',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: Colors.cyan.shade200,
                                letterSpacing: 0.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: _isStreaming ? null : _onWantToSolve,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: Colors.teal.shade400.withOpacity(0.9),
                            width: 1.8,
                          ),
                          gradient: LinearGradient(
                            colors: [
                              Colors.teal.shade900.withOpacity(0.25),
                              Colors.teal.shade700.withOpacity(0.12),
                            ],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.play_circle_outline, size: 18, color: Colors.teal.shade300),
                            const SizedBox(width: 10),
                            Text(
                              'Vreau să o rezolv',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: Colors.teal.shade200,
                                letterSpacing: 0.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          // 5 suggested problem buttons (same style family)
          if (message.suggestedProblems != null &&
              message.suggestedProblems!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Wrap(
                spacing: 10,
                runSpacing: 8,
                children: List.generate(
                  message.suggestedProblems!.length,
                  (i) {
                    final statement = message.suggestedProblems![i];
                    final isDisabled = _isStreaming;
                    return Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: isDisabled ? null : () => _selectSuggestedProblem(statement),
                        borderRadius: BorderRadius.circular(12),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: (Colors.teal.shade300).withOpacity(isDisabled ? 0.4 : 0.85),
                              width: 1.5,
                            ),
                            color: Colors.teal.shade900.withOpacity(isDisabled ? 0.1 : 0.2),
                          ),
                          child: Text(
                            'Problema ${i + 1}',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              color: isDisabled
                                  ? Colors.teal.shade700
                                  : Colors.teal.shade200,
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          // "Rezolvare completă" / "Hint" choice buttons
          if (message.solutionChoiceButtons != null &&
              message.solutionChoiceButtons!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Wrap(
                spacing: 10,
                runSpacing: 8,
                children: List.generate(
                  message.solutionChoiceButtons!.length,
                  (i) {
                    final label = message.solutionChoiceButtons![i];
                    final isDisabled = _isStreaming;
                    return Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: isDisabled ? null : () => _sendSolutionChoice(label),
                        borderRadius: BorderRadius.circular(12),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: (Colors.teal.shade300).withOpacity(isDisabled ? 0.4 : 0.85),
                              width: 1.5,
                            ),
                            color: Colors.teal.shade900.withOpacity(isDisabled ? 0.1 : 0.2),
                          ),
                          child: Text(
                            label,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              color: isDisabled
                                  ? Colors.teal.shade700
                                  : Colors.teal.shade200,
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
        ],
      ),
    ),
    );
  }
}

// Reuse ChatMessage class
class ChatMessage {
  String text;
  final bool isUser;
  final DateTime timestamp;
  bool isStreaming;
  double? timeToFirstToken;
  /// When non-null, show 5 cyan buttons below the bubble to pick a suggested problem.
  List<String>? suggestedProblems;
  /// When non-null, show choice buttons e.g. "Rezolvare completă", "Hint".
  List<String>? solutionChoiceButtons;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.isStreaming = false,
    this.timeToFirstToken,
    this.suggestedProblems,
    this.solutionChoiceButtons,
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

    if (language == 'graph') {
      return _buildGraph(code);
    }

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
    final params = <String, String>{};
    final functions = <String>[];
    final lines = content.trim().split('\n');

    for (final line in lines) {
      final colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        final key = line.substring(0, colonIndex).trim();
        final value = line.substring(colonIndex + 1).trim();

        if (key == 'function' && value.isNotEmpty) {
          functions.add(value);
        } else if (key.startsWith('function') && value.isNotEmpty) {
          final numMatch = RegExp(r'function(\d+)').firstMatch(key);
          if (numMatch != null) {
            final index = int.parse(numMatch.group(1)!);
            while (functions.length < index) {
              functions.add('');
            }
            if (index > 0) {
              functions[index - 1] = value;
            }
          }
        } else {
          params[key] = value;
        }
      }
    }

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
      String expression = functionStr;
      if (expression.contains('=')) {
        expression = expression.split('=').last.trim();
      }

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

      final step = (xMax - xMin) / 200;

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
      return [];
    }

    return points;
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    final lineColors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
    ];

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
