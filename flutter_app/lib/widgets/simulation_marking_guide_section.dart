import "package:flutter/material.dart";

import "../models/exam_solution_step_row.dart";
import "latex_markdown_body.dart";
import "solution_steps_score_table.dart";

/// After the exam ends: barem as Pas / Punctaj table or markdown fallback.
class SimulationMarkingGuideSection extends StatelessWidget {
  /// Creates the post-exam barem block for one problem.
  const SimulationMarkingGuideSection({
    super.key,
    required this.visible,
    required this.markingStepRows,
    this.markingMarkdownFallback,
    this.examProblemId,
  });

  /// When false, returns an empty box (exam still in progress).
  final bool visible;

  /// Structured steps from DB (JSON `[{step, score}, ...]` or markdown tables in barem).
  final List<ExamSolutionStepRow> markingStepRows;

  /// Shown when [markingStepRows] is empty (e.g. plain solution prose).
  final String? markingMarkdownFallback;

  /// `exam_problems.id` for this line (simulation picks a random row per slot).
  final int? examProblemId;

  @override
  Widget build(BuildContext context) {
    if (!visible) {
      return const SizedBox.shrink();
    }

    final ThemeData theme = Theme.of(context);
    final ColorScheme scheme = theme.colorScheme;

    final String? md = markingMarkdownFallback?.trim();
    final bool hasTable = markingStepRows.isNotEmpty;
    final bool hasMd = md != null && md.isNotEmpty;

    if (!hasTable && !hasMd) {
      final String idHint = examProblemId != null
          ? " (enunț exam_problems.id=$examProblemId — verifică dacă este același rând pe care l-ai inspectat)"
          : "";
      return Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Text(
          "Nu există barem / soluție afișabilă pentru acest enunț în datele încărcate.$idHint",
          style: theme.textTheme.bodySmall?.copyWith(
            color: scheme.onSurfaceVariant,
            fontStyle: FontStyle.italic,
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest.withValues(alpha: 0.65),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: scheme.outlineVariant),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(Icons.fact_check_outlined, size: 20, color: scheme.primary),
                  const SizedBox(width: 8),
                  Text(
                    hasTable ? "Barem și punctaj" : "Indicații de rezolvare",
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (hasTable) SolutionStepsScoreTable(rows: markingStepRows),
              if (hasTable && hasMd) const SizedBox(height: 12),
              if (hasMd)
                LatexMarkdownBody(
                  data: md,
                  selectable: true,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
