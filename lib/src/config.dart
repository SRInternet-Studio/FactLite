import 'actions.dart';
import 'rules.dart';

/// Configuration for the FactLite verification framework.
///
/// Encapsulates the rule, retry count, and fallback action into
/// a single reusable configuration object.
///
/// Example:
/// ```dart
/// final config = FactLiteConfig(
///   rule: LLMJudge(apiKey: 'your-key', model: 'gpt-4o-mini'),
///   maxRetries: 2,
///   onFail: ReturnBest(),
/// );
/// ```
class FactLiteConfig {
  /// The rule (judge) to use for evaluating answers.
  final BaseRule rule;

  /// Maximum number of retry attempts after a failed evaluation.
  ///
  /// Defaults to 2.
  final int maxRetries;

  /// The fallback action to execute when all retries are exhausted.
  ///
  /// Defaults to [ReturnBest].
  final FallbackAction onFail;

  FactLiteConfig({
    required this.rule,
    this.maxRetries = 2,
    FallbackAction? onFail,
  }) : onFail = onFail ?? ReturnBest();
}
