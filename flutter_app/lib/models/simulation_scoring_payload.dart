/// One row for `POST /simulari/scoring` [problems] array.
class SimulationProblemScorePayload {
  /// Creates a per-problem score line.
  const SimulationProblemScorePayload({
    required this.subjectNumber,
    required this.problemNumber,
    required this.studentScore,
  });

  final int subjectNumber;
  final int problemNumber;
  final double studentScore;

  /// JSON object for the API body.
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      "subject_number": subjectNumber,
      "problem_number": problemNumber,
      "student_score": studentScore,
    };
  }
}
