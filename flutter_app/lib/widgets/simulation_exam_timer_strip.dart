import "package:flutter/material.dart";

/// Formats [d] as `HH:MM:SS` (clamped to zero if negative).
String formatExamCountdown(Duration d) {
  if (d.isNegative) {
    d = Duration.zero;
  }
  final int h = d.inHours;
  final int m = d.inMinutes.remainder(60);
  final int s = d.inSeconds.remainder(60);
  return "${h.toString().padLeft(2, "0")}:"
      "${m.toString().padLeft(2, "0")}:"
      "${s.toString().padLeft(2, "0")}";
}

/// Bac-style 3h session bar: remaining time + finish action.
class SimulationExamTimerStrip extends StatelessWidget {
  /// Creates the timer strip for an active simulation session.
  const SimulationExamTimerStrip({
    super.key,
    required this.remaining,
    required this.sessionEnded,
    required this.onFinishExamPressed,
  });

  /// Time left until the deadline (caller updates every second).
  final Duration remaining;

  /// True after the user finishes or the countdown hits zero.
  final bool sessionEnded;

  /// Called when the user confirms finishing the exam.
  final VoidCallback onFinishExamPressed;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme scheme = theme.colorScheme;

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: sessionEnded
            ? Row(
                children: <Widget>[
                  Icon(Icons.check_circle_outline, color: scheme.primary, size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "Simularea s-a încheiat.",
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              )
            : LayoutBuilder(
                builder: (BuildContext context, BoxConstraints constraints) {
                  final bool narrow = constraints.maxWidth < 400;
                  final Widget timeBlock = Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Icon(Icons.timer_outlined, color: scheme.primary, size: 22),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            Text(
                              "Timp rămas (3 h)",
                              style: theme.textTheme.labelMedium?.copyWith(
                                color: scheme.onSurfaceVariant,
                              ),
                            ),
                            Text(
                              formatExamCountdown(remaining),
                              style: theme.textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                                fontFeatures: const <FontFeature>[
                                  FontFeature.tabularFigures(),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                  final Widget finishBtn = FilledButton(
                    onPressed: onFinishExamPressed,
                    child: const Text("Încheie examenul"),
                  );
                  if (narrow) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        timeBlock,
                        const SizedBox(height: 12),
                        finishBtn,
                      ],
                    );
                  }
                  return Row(
                    children: <Widget>[
                      Expanded(child: timeBlock),
                      const SizedBox(width: 8),
                      finishBtn,
                    ],
                  );
                },
              ),
      ),
    );
  }
}
