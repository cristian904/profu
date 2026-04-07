import "package:flutter/material.dart";

import "latex_markdown_body.dart";

/// Bottom-sheet content for similar-problem suggestions (LaTeX-aware body + actions).
///
/// Extracted for widget tests and reuse from [SimulationPage].
class SimulariSimilarProblemsSheetBody extends StatelessWidget {
  /// Creates the sheet layout.
  const SimulariSimilarProblemsSheetBody({
    super.key,
    required this.message,
    required this.maxBodyHeight,
    required this.onOpenInSolve,
    required this.onClose,
  });

  /// Assistant message (may contain `$...$` / `$$...$$` LaTeX).
  final String message;

  /// Max height of the scrollable message area.
  final double maxBodyHeight;

  /// User tapped primary CTA (sheet should be popped by caller if needed).
  final VoidCallback onOpenInSolve;

  /// User dismissed without opening Rezolvare.
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              "Probleme similare",
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: maxBodyHeight,
              child: SingleChildScrollView(
                child: LatexMarkdownBody(
                  data: message,
                  selectable: true,
                  shrinkWrap: true,
                ),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: onOpenInSolve,
              child: const Text("Deschide în Rezolvare problemă"),
            ),
            TextButton(
              onPressed: onClose,
              child: const Text("Închide"),
            ),
          ],
        ),
      ),
    );
  }
}
