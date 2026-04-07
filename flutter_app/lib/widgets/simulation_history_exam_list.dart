import "package:flutter/material.dart";

import "../models/simulation_history_entry.dart";

/// Romanian label for [school_subject] DB codes shown in the UI.
String simulationHistorySubjectLabel(String? code) {
  if (code == null || code.isEmpty) {
    return "—";
  }
  switch (code.toLowerCase()) {
    case "mate":
    case "math":
      return "Matematică";
    default:
      return code;
  }
}

/// List of submitted simulations (newest first), under the Istoric chart.
class SimulationHistoryExamList extends StatelessWidget {
  /// Builds the list from [entries] (any order; displayed newest first).
  const SimulationHistoryExamList({
    super.key,
    required this.entries,
    required this.onOpenSimulation,
  });

  /// Scored simulations.
  final List<SimulationHistoryEntry> entries;

  /// User tapped a row: open that simulation on the Simulare tab (review).
  final void Function(int simulationId) onOpenSimulation;

  static String _formatLocalDateTime(DateTime utcOrLocal) {
    final DateTime local = utcOrLocal.toLocal();
    final String d = local.day.toString().padLeft(2, "0");
    final String m = local.month.toString().padLeft(2, "0");
    final String h = local.hour.toString().padLeft(2, "0");
    final String min = local.minute.toString().padLeft(2, "0");
    return "$d.$m.${local.year}, $h:$min";
  }

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }

    final ThemeData theme = Theme.of(context);
    final ColorScheme scheme = theme.colorScheme;

    final List<SimulationHistoryEntry> sorted = List<SimulationHistoryEntry>.from(entries)
      ..sort((SimulationHistoryEntry a, SimulationHistoryEntry b) {
        final int c = b.finishedAt.compareTo(a.finishedAt);
        if (c != 0) {
          return c;
        }
        return b.simulationId.compareTo(a.simulationId);
      });

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            "Simulări anterioare",
            style: theme.textTheme.titleMedium?.copyWith(color: scheme.onSurface),
          ),
          const SizedBox(height: 8),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: sorted.length,
            separatorBuilder: (BuildContext context, int index) => Divider(
              height: 1,
              color: scheme.outlineVariant,
            ),
            itemBuilder: (BuildContext context, int index) {
              final SimulationHistoryEntry e = sorted[index];
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(vertical: 4, horizontal: 0),
                onTap: () {
                  onOpenSimulation(e.simulationId);
                },
                trailing: Icon(
                  Icons.chevron_right,
                  color: scheme.onSurfaceVariant,
                ),
                title: Text(
                  "${e.studentScore.toStringAsFixed(1)} p",
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: scheme.onSurface,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                subtitle: Text(
                  "${_formatLocalDateTime(e.finishedAt)} · "
                  "${simulationHistorySubjectLabel(e.schoolSubject)} · "
                  "Simulare #${e.simulationId}",
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
