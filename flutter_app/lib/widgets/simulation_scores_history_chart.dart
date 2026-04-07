import "package:fl_chart/fl_chart.dart";
import "package:flutter/foundation.dart";
import "package:flutter/material.dart";

import "../models/simulation_history_entry.dart";

/// Line chart of past submitted simulation totals (Istoric tab).
class SimulationScoresHistoryChart extends StatelessWidget {
  /// Builds the chart for [entries] ordered oldest → newest.
  const SimulationScoresHistoryChart({
    super.key,
    required this.entries,
  });

  /// Scored simulations in chronological order.
  final List<SimulationHistoryEntry> entries;

  static String _shortDateLabel(DateTime d) {
    final String day = d.day.toString().padLeft(2, "0");
    final String month = d.month.toString().padLeft(2, "0");
    return "$day.$month";
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme scheme = theme.colorScheme;

    if (entries.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            "Nicio simulare trimisă încă. După ce trimiți punctajele la o simulare, "
            "rezultatele apar aici.",
            style: theme.textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    final List<FlSpot> spots = <FlSpot>[];
    for (int i = 0; i < entries.length; i++) {
      spots.add(FlSpot(i.toDouble(), entries[i].studentScore));
    }

    double minX = 0;
    double maxX = (entries.length - 1).toDouble();
    if (entries.length == 1) {
      minX = -0.25;
      maxX = 0.25;
    }

    double maxScore = 0;
    for (final SimulationHistoryEntry e in entries) {
      if (e.studentScore > maxScore) {
        maxScore = e.studentScore;
      }
    }
    const double minY = 0;
    double maxY = maxScore * 1.12;
    if (maxY < 10) {
      maxY = 10;
    }
    if (maxY > maxScore && maxY - maxScore < 1) {
      maxY = maxScore + 1;
    }

    if (kDebugMode) {
      debugPrint(
        "[SimulationScoresHistoryChart] Rendering ${entries.length} points, maxY=$maxY",
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            "Evoluția punctajelor (simulări trimise)",
            style: theme.textTheme.titleMedium?.copyWith(
              color: scheme.onSurface,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 280,
            width: double.infinity,
            child: LineChart(
              LineChartData(
                clipData: const FlClipData.all(),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: true,
                  horizontalInterval:
                      maxY <= 0 ? 1 : (maxY / 5).clamp(1, double.infinity),
                  getDrawingHorizontalLine: (double value) {
                    return FlLine(
                      color: scheme.outlineVariant,
                      strokeWidth: 1,
                    );
                  },
                  getDrawingVerticalLine: (double value) {
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
                      reservedSize: 44,
                      interval:
                          maxY <= 0 ? 1 : (maxY / 5).clamp(1, double.infinity),
                      getTitlesWidget: (double value, TitleMeta meta) {
                        return Text(
                          value.toStringAsFixed(0),
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
                      reservedSize: 28,
                      interval: entries.length <= 6
                          ? 1
                          : (entries.length / 4).ceilToDouble(),
                      getTitlesWidget: (double value, TitleMeta meta) {
                        final int idx = value.round();
                        if (idx < 0 || idx >= entries.length) {
                          return const SizedBox.shrink();
                        }
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            _shortDateLabel(entries[idx].finishedAt),
                            style: TextStyle(
                              fontSize: 9,
                              color: scheme.onSurfaceVariant,
                            ),
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
                  border: Border.all(color: scheme.outlineVariant),
                ),
                minX: minX,
                maxX: maxX,
                minY: minY,
                maxY: maxY,
                lineBarsData: <LineChartBarData>[
                  LineChartBarData(
                    spots: spots,
                    isCurved: entries.length > 2,
                    color: scheme.primary,
                    barWidth: 3,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter:
                          (FlSpot spot, double xPct, LineChartBarData bar, int index) {
                        return FlDotCirclePainter(
                          radius: 4,
                          color: scheme.primary,
                          strokeWidth: 1,
                          strokeColor: scheme.surface,
                        );
                      },
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color: scheme.primary.withValues(alpha: 0.12),
                    ),
                  ),
                ],
                lineTouchData: LineTouchData(
                  enabled: true,
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipItems: (List<LineBarSpot> touched) {
                      return touched.map((LineBarSpot s) {
                        final int i = s.x.round().clamp(0, entries.length - 1);
                        final SimulationHistoryEntry e = entries[i];
                        return LineTooltipItem(
                          "${e.studentScore.toStringAsFixed(1)} p\n"
                          "${_shortDateLabel(e.finishedAt)}.",
                          TextStyle(
                            color: scheme.onPrimary,
                            fontWeight: FontWeight.w600,
                            fontSize: 12,
                          ),
                        );
                      }).toList();
                    },
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
