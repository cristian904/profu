import "dart:async";
import "dart:convert";

import "package:flutter/foundation.dart";
import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:http/http.dart" as http;
import "package:supabase_flutter/supabase_flutter.dart";

import "../core/config/app_config.dart";
import "../services/simulation_repository.dart";
import "../services/simulation_scoring_api.dart";
import "../widgets/latex_markdown_body.dart";
import "../widgets/profu_drawer.dart";
import "../widgets/simulation_exam_timer_strip.dart";
import "../widgets/simulation_marking_guide_section.dart";
import "../widgets/simulation_scores_submit_footer.dart";

/// Label for Bac-style sub-items: `a)`, `b)`, … (falls back to `1.`, `2.` after `z`).
String _bacSubItemLabel(int index) {
  if (index >= 0 && index < 26) {
    return "${String.fromCharCode(97 + index)})";
  }
  return "${index + 1}.";
}

/// Simulari page with the two required tabs: Istoric and Simulare.
class SimulationPage extends StatefulWidget {
  /// Creates the Simulari page.
  const SimulationPage({super.key});

  @override
  State<SimulationPage> createState() => _SimulationPageState();
}

class _SimulationPageState extends State<SimulationPage> with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final SimulationRepository _simulationRepository = SimulationRepository();

  bool _isGenerating = false;
  int? _lastSimulationId;
  bool _loadingExam = false;
  String? _examLoadError;
  List<SimulationExamProblem> _examProblems = <SimulationExamProblem>[];

  /// Wall-clock instant when the 3h Bac session ends; null when no active countdown.
  DateTime? _examDeadline;

  /// Fires every second to refresh the countdown label.
  Timer? _examCountdownTicker;

  /// True after the user taps finish or the 3h window elapses.
  bool _examSessionEnded = false;

  /// One [TextEditingController] per (subiect, problemă) for self-graded points.
  final Map<String, TextEditingController> _problemScoreControllers =
      <String, TextEditingController>{};

  /// True while per-problem scoring POST is running.
  bool _submittingProblemScores = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    if (kDebugMode) {
      debugPrint("[SIMULARI_UI] SimulationPage initialized");
    }
  }

  @override
  void dispose() {
    _stopExamCountdown();
    _disposeAllProblemScoreControllers();
    _tabController.dispose();
    super.dispose();
  }

  /// Map key for [SimulationExamProblem] score fields.
  String _problemScoreKey(SimulationExamProblem p) {
    return "${p.subjectNumber}_${p.problemNumber}";
  }

  /// Drops controllers for removed slots and creates missing ones.
  void _syncProblemScoreControllers() {
    final Set<String> wanted = _examProblems.map(_problemScoreKey).toSet();
    final List<String> toRemove = _problemScoreControllers.keys
        .where((String k) => !wanted.contains(k))
        .toList();
    for (final String k in toRemove) {
      _problemScoreControllers.remove(k)?.dispose();
    }
    for (final SimulationExamProblem p in _examProblems) {
      final String k = _problemScoreKey(p);
      _problemScoreControllers.putIfAbsent(k, () => TextEditingController());
    }
  }

  /// Disposes every score controller (new exam or page dispose).
  void _disposeAllProblemScoreControllers() {
    for (final TextEditingController c in _problemScoreControllers.values) {
      c.dispose();
    }
    _problemScoreControllers.clear();
  }

  /// Sum of parsed inputs (empty counts as 0) for the footer preview.
  double _sumEnteredScores() {
    double sum = 0;
    for (final SimulationExamProblem p in _examProblems) {
      final TextEditingController? c = _problemScoreControllers[_problemScoreKey(p)];
      final String t = c?.text.trim().replaceAll(",", ".") ?? "";
      if (t.isEmpty) {
        continue;
      }
      final double? v = double.tryParse(t);
      if (v != null) {
        sum += v;
      }
    }
    return sum;
  }

  /// Maximum points for the current exam list (Bac: 90 for 6×5 + 4×15).
  double _maxPossibleScoreTotal() {
    int m = 0;
    for (final SimulationExamProblem p in _examProblems) {
      m += SimulationExamProblem.maxPointsForSubject(p.subjectNumber);
    }
    return m.toDouble();
  }

  /// Stops the periodic ticker (idempotent).
  void _stopExamCountdown() {
    _examCountdownTicker?.cancel();
    _examCountdownTicker = null;
    if (kDebugMode) {
      debugPrint("[SIMULARI_UI] Exam countdown ticker stopped");
    }
  }

  /// Starts a fresh 3h countdown from now (used when the exam payload is loaded).
  void _startExamCountdown() {
    _stopExamCountdown();
    _examDeadline = DateTime.now().add(const Duration(hours: 3));
    _examSessionEnded = false;
    if (kDebugMode) {
      debugPrint("[SIMULARI_UI] Exam countdown started, deadline=$_examDeadline");
    }
    _examCountdownTicker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) {
        return;
      }
      final DateTime? deadline = _examDeadline;
      if (deadline == null || _examSessionEnded) {
        return;
      }
      if (DateTime.now().isAfter(deadline)) {
        _stopExamCountdown();
        setState(() {
          _examSessionEnded = true;
        });
        if (kDebugMode) {
          debugPrint("[SIMULARI_UI] Exam time expired (3h)");
        }
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Timpul de 3 ore s-a scurs."),
          ),
        );
        return;
      }
      setState(() {});
    });
  }

  /// Clears deadline and session flags without leaving a dangling ticker.
  void _resetExamSession() {
    _stopExamCountdown();
    _examDeadline = null;
    _examSessionEnded = false;
    if (kDebugMode) {
      debugPrint("[SIMULARI_UI] Exam session reset");
    }
  }

  /// Remaining time until [_examDeadline], or zero if unset / elapsed.
  Duration _examTimeRemaining() {
    final DateTime? deadline = _examDeadline;
    if (deadline == null) {
      return Duration.zero;
    }
    final Duration left = deadline.difference(DateTime.now());
    return left.isNegative ? Duration.zero : left;
  }

  /// Confirms and ends the exam session from the UI.
  Future<void> _onFinishExamPressed() async {
    if (_examProblems.isEmpty || _examSessionEnded) {
      return;
    }
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) {
        return AlertDialog(
          title: const Text("Încheie examenul"),
          content: const Text(
            "Marchezi simularea ca încheiată? Poți în continuare să citești subiectele.",
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () {
                Navigator.of(ctx).pop(false);
              },
              child: const Text("Anulează"),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(ctx).pop(true);
              },
              child: const Text("Încheie"),
            ),
          ],
        );
      },
    );
    if (confirmed != true || !mounted) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Finish exam cancelled or unmounted");
      }
      return;
    }
    _stopExamCountdown();
    setState(() {
      _examSessionEnded = true;
    });
    if (kDebugMode) {
      debugPrint("[SIMULARI_UI] Exam finished by user");
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text("Simularea a fost marcată ca încheiată."),
      ),
    );
  }

  /// Validates each problem score, POSTs `/simulari/scoring` with all lines, shows server total.
  Future<void> _onSubmitAllProblemScoresPressed() async {
    final int? simId = _lastSimulationId;
    if (simId == null || !_examSessionEnded || _examProblems.isEmpty) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Submit problem scores ignored: invalid state");
      }
      return;
    }

    final List<SimulationProblemScorePayload> payload = <SimulationProblemScorePayload>[];
    for (final SimulationExamProblem p in _examProblems) {
      final int maxP = SimulationExamProblem.maxPointsForSubject(p.subjectNumber);
      final TextEditingController? c = _problemScoreControllers[_problemScoreKey(p)];
      final String raw = c?.text.trim().replaceAll(",", ".") ?? "";
      final double score;
      if (raw.isEmpty) {
        score = 0;
      } else {
        final double? parsed = double.tryParse(raw);
        if (parsed == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                "Punctaj invalid la Subiectul ${p.subjectNumber}, problema ${p.problemNumber}.",
              ),
            ),
          );
          return;
        }
        if (parsed < 0 || parsed > maxP) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                "La Subiectul ${p.subjectNumber}, problema ${p.problemNumber}: "
                "punctajul trebuie să fie între 0 și $maxP.",
              ),
            ),
          );
          return;
        }
        score = parsed;
      }
      payload.add(
        SimulationProblemScorePayload(
          subjectNumber: p.subjectNumber,
          problemNumber: p.problemNumber,
          studentScore: score,
        ),
      );
    }

    final String? accessToken = Supabase.instance.client.auth.currentSession?.accessToken;
    if (accessToken == null || accessToken.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Trebuie să fii autentificat pentru a trimite scorul."),
        ),
      );
      return;
    }

    setState(() {
      _submittingProblemScores = true;
    });

    try {
      final double persisted = await submitSimulationPerProblemScores(
        accessToken: accessToken,
        simulationId: simId,
        problems: payload,
      );
      if (!mounted) {
        return;
      }
      if (kDebugMode) {
        debugPrint(
          "[SIMULARI_UI] Per-problem scores saved total=$persisted simulation_id=$simId",
        );
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Punctaje salvate. Total: $persisted p"),
        ),
      );
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Submit problem scores error: $error");
        debugPrint("[SIMULARI_UI] Submit problem scores stack: $stackTrace");
      }
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Eroare la trimitere: $error"),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _submittingProblemScores = false;
        });
      }
    }
  }

  /// Loads problem statements from Supabase after the backend created the simulation.
  Future<void> _loadExamFromSupabase(int simulationId) async {
    setState(() {
      _loadingExam = true;
      _examLoadError = null;
    });
    try {
      final List<SimulationExamProblem> problems =
          await _simulationRepository.fetchSimulationProblemsForCurrentUser(
        simulationId: simulationId,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _examProblems = problems;
        _loadingExam = false;
      });
      _syncProblemScoreControllers();
      if (!mounted) {
        return;
      }
      if (problems.isNotEmpty) {
        _startExamCountdown();
      } else {
        _resetExamSession();
      }
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Load exam error: $error");
        debugPrint("[SIMULARI_UI] Load exam stack: $stackTrace");
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _examProblems = <SimulationExamProblem>[];
        _loadingExam = false;
        _examLoadError = error.toString();
      });
      _disposeAllProblemScoreControllers();
      _resetExamSession();
    }
  }

  /// Calls backend endpoint to create a new simulation, then loads the exam from Supabase.
  Future<void> _onGeneratePressed() async {
    if (_isGenerating) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate ignored: request already in progress");
      }
      return;
    }

    _disposeAllProblemScoreControllers();
    setState(() {
      _isGenerating = true;
      _examProblems = <SimulationExamProblem>[];
      _examLoadError = null;
    });
    _resetExamSession();

    try {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate button pressed");
      }

      final String? accessToken = Supabase.instance.client.auth.currentSession?.accessToken;
      if (accessToken == null || accessToken.isEmpty) {
        throw Exception("Missing auth session. Please sign in again.");
      }

      final Uri endpoint = Uri.parse("${AppConfig.apiBaseUrl}/simulari/generate");
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Calling endpoint: $endpoint");
      }

      final http.Response response = await http.post(
        endpoint,
        headers: <String, String>{
          "Content-Type": "application/json",
          "Authorization": "Bearer $accessToken",
        },
        body: jsonEncode(<String, dynamic>{
          "school_subject": "mate",
        }),
      );

      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate response status: ${response.statusCode}");
        debugPrint("[SIMULARI_UI] Generate response body: ${response.body}");
      }

      if (response.statusCode != 201) {
        String errorMessage = "Nu am putut genera simularea.";
        try {
          final Map<String, dynamic> payload = jsonDecode(response.body) as Map<String, dynamic>;
          final dynamic detail = payload["detail"];
          if (detail != null && detail.toString().isNotEmpty) {
            errorMessage = detail.toString();
          }
        } catch (_) {
          // Keep default message if body is not valid JSON.
        }
        throw Exception(errorMessage);
      }

      final Map<String, dynamic> payload = jsonDecode(response.body) as Map<String, dynamic>;
      final int simulationId = payload["simulation_id"] as int;
      setState(() {
        _lastSimulationId = simulationId;
      });

      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Simulare generata. Se incarca subiectele..."),
        ),
      );

      await _loadExamFromSupabase(simulationId);

      if (!mounted) {
        return;
      }
      if (_examLoadError == null && _examProblems.isNotEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Examenul a fost incarcat. Succes la simulare!"),
          ),
        );
      }
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint("[SIMULARI_UI] Generate error: $error");
        debugPrint("[SIMULARI_UI] Generate stack: $stackTrace");
      }
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Eroare la generare: $error"),
        ),
      );
    } finally {
      if (!mounted) {
        return;
      }
      setState(() {
        _isGenerating = false;
      });
    }
  }

  /// Clears the on-screen exam so the user can generate another one.
  void _onClearExam() {
    _resetExamSession();
    _disposeAllProblemScoreControllers();
    setState(() {
      _examProblems = <SimulationExamProblem>[];
      _lastSimulationId = null;
      _examLoadError = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Simulari"),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: "Istoric"),
            Tab(text: "Simulare"),
          ],
        ),
      ),
      drawer: const ProfuDrawer(),
      body: TabBarView(
        controller: _tabController,
        children: [
          Center(
            child: Text(
              "Istoricul simularilor va fi afisat aici.",
              style: Theme.of(context).textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
          ),
          _buildSimulareTab(context),
        ],
      ),
    );
  }

  Widget _buildSimulareTab(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Row(
            children: <Widget>[
              Expanded(
                child: ElevatedButton(
                  onPressed: _isGenerating ? null : _onGeneratePressed,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  ),
                  child: _isGenerating
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text("Genereaza"),
                ),
              ),
              if (_examProblems.isNotEmpty) ...<Widget>[
                const SizedBox(width: 8),
                TextButton(
                  onPressed: _onClearExam,
                  child: const Text("Sterge"),
                ),
              ],
            ],
          ),
        ),
        if (_loadingExam)
          const LinearProgressIndicator(minHeight: 2),
        if (_lastSimulationId != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              "Simulare #$_lastSimulationId",
              style: theme.textTheme.labelLarge,
            ),
          ),
        if (_examLoadError != null)
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              "Nu s-a putut incarca examenul: $_examLoadError",
              style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.error),
            ),
          ),
        if (_examProblems.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: SimulationExamTimerStrip(
              remaining: _examTimeRemaining(),
              sessionEnded: _examSessionEnded,
              onFinishExamPressed: _onFinishExamPressed,
            ),
          ),
        Expanded(
          child: _examProblems.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      _loadingExam
                          ? "Se incarca subiectele..."
                          : "Apasa Genereaza pentru a crea o simulare. Dupa generare, subiectele apar aici.",
                      style: theme.textTheme.bodyLarge,
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                  itemCount: _listItemCount(),
                  itemBuilder: (BuildContext context, int index) {
                    return _buildListItem(context, index);
                  },
                ),
        ),
        if (_examProblems.isNotEmpty &&
            _examSessionEnded &&
            _lastSimulationId != null)
          SimulationScoresSubmitFooter(
            sumPoints: _sumEnteredScores(),
            maxPointsTotal: _maxPossibleScoreTotal(),
            isSubmitting: _submittingProblemScores,
            onSubmitPressed: _onSubmitAllProblemScoresPressed,
          ),
      ],
    );
  }

  int _listItemCount() {
    int count = 0;
    int? lastSubject;
    for (final SimulationExamProblem p in _examProblems) {
      if (lastSubject != p.subjectNumber) {
        count += 1;
        lastSubject = p.subjectNumber;
      }
      count += 1;
    }
    return count;
  }

  Widget _buildListItem(BuildContext context, int index) {
    int i = 0;
    int? lastSubject;
    for (final SimulationExamProblem p in _examProblems) {
      if (lastSubject != p.subjectNumber) {
        if (i == index) {
          return _buildSectionHeader(context, p.subjectNumber);
        }
        i += 1;
        lastSubject = p.subjectNumber;
      }
      if (i == index) {
        return _buildProblemCard(context, p);
      }
      i += 1;
    }
    return const SizedBox.shrink();
  }

  Widget _buildSectionHeader(BuildContext context, int subjectNumber) {
    final ThemeData theme = Theme.of(context);
    final int maxPer = SimulationExamProblem.maxPointsForSubject(subjectNumber);
    return Padding(
      padding: const EdgeInsets.only(top: 16, bottom: 8),
      child: Text(
        "${SimulationExamProblem.sectionTitle(subjectNumber)} (cate $maxPer p fiecare)",
        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget _buildProblemCard(BuildContext context, SimulationExamProblem p) {
    final ThemeData theme = Theme.of(context);
    final int maxP = SimulationExamProblem.maxPointsForSubject(p.subjectNumber);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              "Problema ${p.problemNumber} — maxim $maxP p",
              style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
            ),
            if (p.topic != null && p.topic!.isNotEmpty) ...<Widget>[
              const SizedBox(height: 4),
              Text(
                p.topic!,
                style: theme.textTheme.labelMedium?.copyWith(
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
            const SizedBox(height: 8),
            LatexMarkdownBody(
              data: p.statement,
              selectable: true,
            ),
            if (p.items.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              Text(
                "Cerințe:",
                style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
              ),
              ...List<Widget>.generate(p.items.length, (int i) {
                return Padding(
                  padding: EdgeInsets.only(top: i == 0 ? 6 : 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          "${_bacSubItemLabel(i)} ",
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Expanded(
                        child: LatexMarkdownBody(
                          data: p.items[i],
                          selectable: true,
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
            SimulationMarkingGuideSection(
              visible: _examSessionEnded,
              markingStepRows: p.markingStepRows,
              markingMarkdownFallback: p.markingMarkdownFallback,
              examProblemId: p.examProblemId,
            ),
            if (_examSessionEnded) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                "Punctajul tău (max $maxP p)",
                style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _problemScoreControllers[_problemScoreKey(p)]!,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                inputFormatters: <TextInputFormatter>[
                  FilteringTextInputFormatter.allow(RegExp(r"[0-9.,]")),
                ],
                onChanged: (String _) {
                  setState(() {});
                },
                decoration: InputDecoration(
                  hintText: "0–$maxP",
                  border: const OutlineInputBorder(),
                  suffixText: "p",
                  isDense: true,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
