import 'package:flutter/material.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:markdown/markdown.dart' as md;

void main() {
  runApp(const LatexPreviewApp());
}

class LatexPreviewApp extends StatelessWidget {
  const LatexPreviewApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LaTeX Preview',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue, brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: const PreviewPage(),
    );
  }
}

class PreviewPage extends StatefulWidget {
  const PreviewPage({super.key});

  @override
  State<PreviewPage> createState() => _PreviewPageState();
}

class _PreviewPageState extends State<PreviewPage> {
  final TextEditingController _controller = TextEditingController();
  String _renderedText = '';

  void _onPreview() {
    setState(() {
      _renderedText = _controller.text;
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      appBar: AppBar(
        title: const Text('LaTeX / Markdown Preview'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _controller,
              maxLines: 12,
              decoration: InputDecoration(
                hintText: 'Paste markdown/LaTeX here (\$...\$ or \$\$...\$\$), then tap Preview',
                border: const OutlineInputBorder(),
                filled: true,
              ),
              onSubmitted: (_) => _onPreview(),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: FilledButton.icon(
              onPressed: _onPreview,
              icon: const Icon(Icons.preview),
              label: const Text('Preview'),
            ),
          ),
          const Divider(height: 24),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: _renderedText.isEmpty
                  ? Text(
                      'Enter text and tap Preview.',
                      style: TextStyle(color: isDark ? Colors.grey[400] : Colors.grey[600]),
                    )
                  : MarkdownBody(
                      data: _renderedText,
                      selectable: true,
                      builders: {
                        'latex': _LatexElementBuilder(),
                        'code': _CodeElementBuilder(),
                      },
                      inlineSyntaxes: [_LatexInlineSyntax()],
                      styleSheet: MarkdownStyleSheet(
                        p: TextStyle(
                          color: isDark ? Colors.white : Colors.black87,
                          fontSize: 16,
                          height: 1.5,
                        ),
                        strong: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : Colors.black87,
                        ),
                        em: const TextStyle(fontStyle: FontStyle.italic),
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
                        h1: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : Colors.black87,
                        ),
                        h2: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : Colors.black87,
                        ),
                        h3: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : Colors.black87,
                        ),
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Same as main app: parses $...$ and $$...$$
class _LatexInlineSyntax extends md.InlineSyntax {
  _LatexInlineSyntax() : super(r'\$\$(.+?)\$\$|\$(.+?)\$');

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

/// Same as main app: renders with flutter_math_fork
class _LatexElementBuilder extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final latex = element.textContent;
    final isBlock = element.attributes['display'] == 'block';

    return Builder(
      builder: (context) {
        final isDark = Theme.of(context).brightness == Brightness.dark;
        try {
          return Padding(
            padding: isBlock ? const EdgeInsets.symmetric(vertical: 8) : EdgeInsets.zero,
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

class _CodeElementBuilder extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final code = element.textContent;
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
}
