/// Rules for Simulari "probleme similare" UX (visibility and conversation titling).

/// Whether each problem card should show the "Probleme similare" icon.
///
/// Shown after the live exam ends, or when reviewing a simulation opened from Istoric.
bool simulariShowSimilarProblemsIcon({
  required bool examSessionEnded,
  required bool viewingPastSimulation,
}) {
  return examSessionEnded || viewingPastSimulation;
}

/// Prefix for the Rezolvare conversation title when user opens chat from this flow.
String simulariSimilarProblemsConversationPrefix({
  required bool viewingPastSimulation,
}) {
  return viewingPastSimulation ? "Istoric simulare" : "Simulare";
}
