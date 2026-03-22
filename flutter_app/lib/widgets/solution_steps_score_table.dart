import "package:flutter/material.dart";

import "../models/exam_solution_step_row.dart";
import "latex_markdown_body.dart";

/// Formats [score] for the Punctaj column (whole numbers without trailing .0).
String formatStepScoreForTable(double? score) {
  if (score == null) {
    return "—";
  }
  final double r = double.parse(score.toStringAsFixed(4));
  if (r == r.roundToDouble()) {
    return "${r.toInt()}";
  }
  return r.toString();
}

/// Table of solution steps: one row per `{ step, score }` item; columns [Pas, Punctaj].
class SolutionStepsScoreTable extends StatelessWidget {
  /// Creates a table from structured [rows] (list of objects with step + score).
  const SolutionStepsScoreTable({
    super.key,
    required this.rows,
  });

  /// Non-empty list from JSON `solution_steps`: `[{ "step": "...", "score": 1 }, ...]`.
  final List<ExamSolutionStepRow> rows;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) {
      return const SizedBox.shrink();
    }

    final ThemeData theme = Theme.of(context);
    final ColorScheme scheme = theme.colorScheme;
    final TextStyle headerStyle = theme.textTheme.labelLarge!.copyWith(
      fontWeight: FontWeight.w600,
      color: scheme.onSurface,
    );
    final TextStyle cellStyle = theme.textTheme.bodyMedium!.copyWith(
      color: scheme.onSurface,
    );

    return Table(
      border: TableBorder.all(
        color: scheme.outlineVariant,
        width: 1,
      ),
      columnWidths: const <int, TableColumnWidth>{
        0: FlexColumnWidth(1),
        1: FixedColumnWidth(88),
      },
      defaultVerticalAlignment: TableCellVerticalAlignment.top,
      children: <TableRow>[
        TableRow(
          decoration: BoxDecoration(
            color: scheme.surfaceContainerHigh.withValues(alpha: 0.85),
          ),
          children: <Widget>[
            _headerCell("Pas", headerStyle, scheme),
            _headerCell("Punctaj", headerStyle, scheme),
          ],
        ),
        ...List<TableRow>.generate(rows.length, (int i) {
          final ExamSolutionStepRow r = rows[i];
          return TableRow(
            children: <Widget>[
              _tableBodyCell(
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: LatexMarkdownBody(
                    data: r.step,
                    selectable: true,
                    shrinkWrap: true,
                  ),
                ),
              ),
              _tableBodyCell(
                Padding(
                  padding: const EdgeInsets.all(10),
                  child: Text(
                    formatStepScoreForTable(r.score),
                    style: cellStyle.copyWith(fontWeight: FontWeight.w500),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ],
          );
        }),
      ],
    );
  }

  /// Header cell with padding and background from [TableRow] decoration.
  Widget _headerCell(String label, TextStyle style, ColorScheme scheme) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      child: Text(
        label,
        style: style,
      ),
    );
  }

  /// Wraps a [TableRow] cell.
  Widget _tableBodyCell(Widget child) {
    return TableCell(child: child);
  }
}
