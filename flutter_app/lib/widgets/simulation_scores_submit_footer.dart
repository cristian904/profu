import "package:flutter/material.dart";

/// Formats [v] for the footer label (no unnecessary decimals).
String formatPointsForFooter(double v) {
  if (v == v.roundToDouble()) {
    return "${v.toInt()}";
  }
  return v.toStringAsFixed(1);
}

/// Pinned footer: running sum of per-problem scores and submit button.
class SimulationScoresSubmitFooter extends StatelessWidget {
  /// Creates the submit bar for per-problem scoring.
  const SimulationScoresSubmitFooter({
    super.key,
    required this.sumPoints,
    required this.maxPointsTotal,
    required this.isSubmitting,
    required this.onSubmitPressed,
  });

  /// Sum of entered scores (empty fields count as 0).
  final double sumPoints;

  /// Maximum possible total for this exam (e.g. 90 for standard Bac mate).
  final double maxPointsTotal;

  /// True while the HTTP request runs.
  final bool isSubmitting;

  /// Called when the user submits all problem scores.
  final VoidCallback onSubmitPressed;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme scheme = theme.colorScheme;

    return Material(
      elevation: 6,
      color: scheme.surface,
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(Icons.summarize_outlined, color: scheme.primary, size: 22),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      "Total: ${formatPointsForFooter(sumPoints)} / ${formatPointsForFooter(maxPointsTotal)} p",
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              FilledButton(
                onPressed: isSubmitting ? null : onSubmitPressed,
                child: isSubmitting
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text("Trimite toate punctajele"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
