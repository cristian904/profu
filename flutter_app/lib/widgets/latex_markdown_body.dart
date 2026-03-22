import "package:flutter/material.dart";
import "package:flutter_markdown/flutter_markdown.dart";
import "package:flutter_math_fork/flutter_math.dart";
import "package:markdown/markdown.dart" as md;

/// Inline `$...$` and `$$...$$` for [MarkdownBody] (same idea as clarify chat).
class LatexInlineSyntax extends md.InlineSyntax {
  /// Creates the LaTeX inline parser.
  LatexInlineSyntax() : super(r"\$\$(.+?)\$\$|\$(.+?)\$");

  @override
  bool onMatch(md.InlineParser parser, Match match) {
    final String? latex = match.group(1) ?? match.group(2);
    if (latex == null) {
      return false;
    }

    final bool isBlock = match.group(0)!.startsWith(r"$$");
    final md.Element element = md.Element.text("latex", latex);
    element.attributes["display"] = isBlock ? "block" : "inline";
    parser.addNode(element);
    return true;
  }
}

/// Renders custom `latex` elements with [Math.tex].
class LatexElementBuilder extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final String latex = element.textContent;
    final bool isBlock = element.attributes["display"] == "block";

    return Builder(
      builder: (BuildContext context) {
        final ColorScheme scheme = Theme.of(context).colorScheme;

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
            isBlock ? "\$\$$latex\$\$" : "\$$latex\$",
            style: TextStyle(
              color: scheme.error,
              fontFamily: "monospace",
              fontSize: 14,
            ),
          );
        }
      },
    );
  }
}

/// Simple code blocks (no `graph` language) for exam-style markdown.
class SimpleMarkdownCodeElementBuilder extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    final String code = element.textContent;

    return Builder(
      builder: (BuildContext context) {
        final ColorScheme scheme = Theme.of(context).colorScheme;
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
              fontFamily: "monospace",
              fontSize: 14,
              color: scheme.onSurface,
            ),
          ),
        );
      },
    );
  }
}

/// Markdown body with LaTeX via `$...$` / `$$...$$`, aligned with clarify chat styling.
class LatexMarkdownBody extends StatelessWidget {
  /// Creates a markdown + LaTeX body for exam statements and similar text.
  const LatexMarkdownBody({
    super.key,
    required this.data,
    this.selectable = true,
    this.shrinkWrap = true,
  });

  /// Raw markdown / mixed text (may contain `$...$` LaTeX).
  final String data;
  final bool selectable;
  final bool shrinkWrap;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;

    return MarkdownBody(
      data: data,
      selectable: selectable,
      shrinkWrap: shrinkWrap,
      fitContent: true,
      builders: <String, MarkdownElementBuilder>{
        "latex": LatexElementBuilder(),
        "code": SimpleMarkdownCodeElementBuilder(),
      },
      inlineSyntaxes: <md.InlineSyntax>[LatexInlineSyntax()],
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
          fontFamily: "monospace",
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
    );
  }
}
