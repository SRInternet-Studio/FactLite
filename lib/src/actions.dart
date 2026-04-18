import 'package:logging/logging.dart';

final _logger = Logger('FactLite.Actions');

/// Evaluation result returned by rules.
class EvaluationResult {
  /// Whether the answer passed the evaluation.
  final bool isPass;

  /// Feedback from the judge. Empty string if passed.
  final String feedback;

  const EvaluationResult({required this.isPass, this.feedback = ''});

  factory EvaluationResult.fromMap(Map<String, dynamic> map) {
    return EvaluationResult(
      isPass: map['is_pass'] as bool? ?? false,
      feedback: map['feedback'] as String? ?? '',
    );
  }

  Map<String, dynamic> toMap() {
    return {'is_pass': isPass, 'feedback': feedback};
  }

  @override
  String toString() => 'EvaluationResult(isPass: $isPass, feedback: $feedback)';
}

/// Base class for all fallback actions.
///
/// A fallback action defines what happens when the answer fails
/// all verification retries.
abstract class FallbackAction {
  /// Execute the fallback action.
  ///
  /// [prompt] is the original user question.
  /// [lastAnswer] is the model's last generated answer.
  /// [feedback] is the feedback from the judge.
  ///
  /// Returns the fallback action's response.
  Future<String> execute({
    required String prompt,
    required String lastAnswer,
    required String feedback,
  });
}

/// Return the last generated answer despite failing verification.
class ReturnBest extends FallbackAction {
  @override
  Future<String> execute({
    required String prompt,
    required String lastAnswer,
    required String feedback,
  }) async {
    _logger.warning(
      'Returning the last generated answer despite failing verification.',
    );
    return lastAnswer;
  }
}

/// Raise an exception if the answer fails verification.
class RaiseError extends FallbackAction {
  @override
  Future<String> execute({
    required String prompt,
    required String lastAnswer,
    required String feedback,
  }) async {
    _logger.severe('Raising exception due to factual verification failure.');
    throw FactLiteVerificationException(
      'Answer failed factual verification. Last feedback: $feedback',
    );
  }
}

/// Exception thrown when verification fails and [RaiseError] is used.
class FactLiteVerificationException implements Exception {
  final String message;
  const FactLiteVerificationException(this.message);

  @override
  String toString() => 'FactLiteVerificationException: $message';
}

/// Return a safe message if the answer fails verification.
class ReturnSafeMessage extends FallbackAction {
  /// The safe message to return.
  final String safeMessage;

  ReturnSafeMessage({this.safeMessage = '抱歉，AI 暂时无法针对该问题给出有确切把握的回答。'});

  @override
  Future<String> execute({
    required String prompt,
    required String lastAnswer,
    required String feedback,
  }) async {
    _logger.warning(
      'Returning safe message. Original hallucination feedback: $feedback',
    );
    return safeMessage;
  }
}
