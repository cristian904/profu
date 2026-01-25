import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import 'package:markdown/markdown.dart' as md;
import 'package:fl_chart/fl_chart.dart';
import 'package:math_expressions/math_expressions.dart';

class ClarifyChatPage extends StatefulWidget {
  const ClarifyChatPage({super.key});

  @override
  State<ClarifyChatPage> createState() => _ClarifyChatPageState();
}

class _ClarifyChatPageState extends State<ClarifyChatPage> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isStreaming = false;

  final String _apiUrl = 'http://localhost:8000/clarify/stream';

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
      
      request.body = json.encode({
        'query': message,
        'history': history,
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
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('N-am înțeles la clasă'),
        centerTitle: true,
      ),
      body: Column(
        children: [
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
                          color: Colors.orange.withOpacity(0.5),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Pune o întrebare despre ce nu ai înțeles!',
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                color: Colors.grey[600],
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
                  color: Colors.black.withOpacity(0.1),
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
                      enabled: !_isStreaming,
                    ),
                  ),
                  const SizedBox(width: 8),
                  FloatingActionButton(
                    onPressed: _isStreaming ? null : _sendMessage,
                    child: _isStreaming
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
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
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: message.isUser
              ? Theme.of(context).colorScheme.primary
              : (isDark ? const Color(0xFF2C2C2C) : Colors.grey[200]),
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
                        ? Colors.white 
                        : (isDark ? Colors.white : Colors.black87),
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
                      color: isDark ? Colors.white : Colors.black87,
                      fontSize: 16,
                      height: 1.5,
                    ),
                    strong: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : Colors.black,
                    ),
                    em: const TextStyle(
                      fontStyle: FontStyle.italic,
                    ),
                    code: TextStyle(
                      backgroundColor: isDark ? const Color(0xFF1E1E1E) : Colors.grey[300],
                      color: isDark ? Colors.white : Colors.black87,
                      fontFamily: 'monospace',
                      fontSize: 14,
                    ),
                    codeblockPadding: const EdgeInsets.all(8),
                    codeblockDecoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E1E1E) : Colors.grey[300],
                      borderRadius: BorderRadius.circular(8),
                    ),
                    blockquote: TextStyle(
                      color: isDark ? Colors.grey[400] : Colors.grey[700],
                      fontStyle: FontStyle.italic,
                    ),
                    blockquotePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    blockquoteDecoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E1E1E) : Colors.grey[100],
                      borderRadius: BorderRadius.circular(4),
                      border: Border(
                        left: BorderSide(
                          color: isDark ? Colors.grey[600]! : Colors.grey[400]!,
                          width: 4,
                        ),
                      ),
                    ),
                    h1: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : Colors.black87,
                      height: 1.5,
                    ),
                    h2: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : Colors.black87,
                      height: 1.4,
                    ),
                    h3: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : Colors.black87,
                      height: 1.3,
                    ),
                    listBullet: TextStyle(
                      color: isDark ? Colors.white : Colors.black87,
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
                        ? Colors.white 
                        : (isDark ? Colors.grey[400] : Colors.grey[700]),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class ChatMessage {
  String text;
  final bool isUser;
  final DateTime timestamp;
  bool isStreaming;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.isStreaming = false,
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
        final isDark = Theme.of(context).brightness == Brightness.dark;
        
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
                color: isDark ? Colors.white : Colors.black87,
              ),
            ),
          );
        } catch (e) {
          // If LaTeX parsing fails, display the raw text
          return Text(
            isBlock ? '\$\$$latex\$\$' : '\$$latex\$',
            style: TextStyle(
              color: Colors.red[700],
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
        final isDark = Theme.of(context).brightness == Brightness.dark;
        return Container(
          padding: const EdgeInsets.all(12),
          margin: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E1E1E) : Colors.grey[300],
            borderRadius: BorderRadius.circular(8),
          ),
          child: SelectableText(
            code,
            style: TextStyle(
              fontFamily: 'monospace',
              fontSize: 14,
              color: isDark ? Colors.white : Colors.black87,
            ),
          ),
        );
      },
    );
  }

  Widget _buildGraph(String content) {
    // Parse the graph definition
    final params = <String, String>{};
    final lines = content.trim().split('\n');
    
    for (final line in lines) {
      final colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        final key = line.substring(0, colonIndex).trim();
        final value = line.substring(colonIndex + 1).trim();
        params[key] = value;
      }
    }

    if (params['function'] == null || params['function']!.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        margin: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: Colors.red[100],
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Text(
          'Invalid graph: missing function parameter',
          style: TextStyle(color: Colors.red),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: FunctionGraphWidget(
        functionStr: params['function']!,
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
  final String functionStr;
  final double xMin;
  final double xMax;
  final double yMin;
  final double yMax;
  final String? title;

  const FunctionGraphWidget({
    super.key,
    required this.functionStr,
    required this.xMin,
    required this.xMax,
    required this.yMin,
    required this.yMax,
    this.title,
  });

  List<FlSpot> _generatePoints() {
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
    final points = _generatePoints();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (points.isEmpty) {
      return Container(
        height: 250,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.red[100],
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            'Could not render graph for: $functionStr',
            style: const TextStyle(color: Colors.red),
          ),
        ),
      );
    }

    return Container(
      height: 250,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1E1E) : Colors.grey[100],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDark ? Colors.grey[700]! : Colors.grey[300]!,
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
                  color: isDark ? Colors.white : Colors.black87,
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
                      color: isDark ? Colors.grey[800]! : Colors.grey[300]!,
                      strokeWidth: 1,
                    );
                  },
                  getDrawingVerticalLine: (value) {
                    return FlLine(
                      color: isDark ? Colors.grey[800]! : Colors.grey[300]!,
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
                            color: isDark ? Colors.white : Colors.black87,
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
                            color: isDark ? Colors.white : Colors.black87,
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
                    color: isDark ? Colors.grey[700]! : Colors.grey[400]!,
                  ),
                ),
                minX: xMin,
                maxX: xMax,
                minY: yMin,
                maxY: yMax,
                lineBarsData: [
                  LineChartBarData(
                    spots: points,
                    isCurved: true,
                    color: Colors.blue,
                    barWidth: 2,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(show: false),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              functionStr,
              style: TextStyle(
                fontSize: 12,
                fontStyle: FontStyle.italic,
                color: isDark ? Colors.grey[400] : Colors.black54,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
