import 'package:logging/logging.dart';
import 'actions.dart';
import 'config.dart';
import 'rules.dart';

final _logger = Logger('FactLite');

/// Type definition for an LLM generator function.
///
/// Takes a prompt string and returns a [Future<String>] with the answer.
typedef LlmGenerator = Future<String> Function(String prompt);

/// Generate a reflection prompt for self-correction.
String _generateReflectionPrompt(
  String promptValue,
  String bestAnswer,
  String feedback,
) {
  return '''[System Prompt: You need to self-reflect and self-correct]
Original user question: $promptValue
Your previous answer: $bestAnswer
Judge's feedback: $feedback
Please take a deep breath, strictly correct the errors mentioned above, and provide the final perfect answer.''';
}

/// Verify an LLM's answer using the configured rule and retry logic.
///
/// This is the core function of the FactLite framework. It implements
/// the **Generate -> Evaluate -> Reflect** loop:
///
/// 1. **Generate**: Call the [generator] function to produce an initial draft.
/// 2. **Evaluate**: Use the configured [rule] to assess the answer.
/// 3. **Reflect & Retry**: If evaluation fails, create a reflection prompt
///    and retry up to [maxRetries] times.
/// 4. **Fallback**: If all retries fail, execute the [onFail] action.
///
/// Parameters can be provided individually or via a [FactLiteConfig] object.
///
/// Example:
/// ```dart
/// final result = await verify(
///   prompt: 'Was Li Bai an emperor in the Song Dynasty?',
///   generator: (prompt) async {
///     // Your LLM API call here
///     return await callOpenAI(prompt);
///   },
///   rule: LLMJudge(apiKey: 'your-key'),
///   maxRetries: 2,
///   onFail: ReturnBest(),
/// );
/// ```
Future<String> verify({
  required String prompt,
  required LlmGenerator generator,
  BaseRule? rule,
  int? maxRetries,
  FallbackAction? onFail,
  FactLiteConfig? config,
}) async {
  // Resolve configuration: config object takes precedence
  final effectiveRule = config?.rule ?? rule;
  final effectiveMaxRetries = config?.maxRetries ?? maxRetries ?? 2;
  final effectiveOnFail = config?.onFail ?? onFail ?? ReturnBest();

  if (effectiveRule == null) {
    throw ArgumentError(
      'A rule must be provided either directly or via a FactLiteConfig.',
    );
  }

  int retryCount = 0;
  String? bestAnswer;
  String currentPrompt = prompt;
  String feedback = '';

  while (retryCount <= effectiveMaxRetries) {
    if (retryCount == 0) {
      _logger.info('Generating initial answer...');
    } else {
      _logger.warning(
        'Triggering reflection and rewrite, attempt $retryCount...',
      );
    }

    // Generate answer
    final answer = await generator(currentPrompt);
    bestAnswer = answer;

    // Evaluate answer quality
    _logger.info('Evaluating answer quality...');
    final evaluationResult = await effectiveRule.evaluate(prompt, answer);
    final isPass = evaluationResult.isPass;
    feedback = evaluationResult.feedback;

    if (isPass) {
      if (retryCount > 0) {
        _logger.info('✅ Correction successful, returning the verified answer!');
      } else {
        _logger.info('✅ Initial draft is flawless, passing through!');
      }
      return answer;
    }

    _logger.severe('❌ Hallucination or error detected: $feedback');

    // Generate reflection prompt for retry
    currentPrompt = _generateReflectionPrompt(prompt, bestAnswer, feedback);
    retryCount++;
  }

  _logger.warning('Maximum retries reached, executing fallback strategy.');
  return effectiveOnFail.execute(
    prompt: prompt,
    lastAnswer: bestAnswer ?? '',
    feedback: feedback,
  );
}

/// A wrapper class that creates a verified version of an LLM generator function.
///
/// This is a convenience class that binds a [FactLiteConfig] to a generator
/// function, similar to how Python's `@verify` decorator wraps a function.
///
/// Example:
/// ```dart
/// final verifiedAsk = VerifiedGenerator(
///   config: FactLiteConfig(
///     rule: LLMJudge(apiKey: 'your-key'),
///     maxRetries: 2,
///   ),
///   generator: (prompt) async {
///     return await callOpenAI(prompt);
///   },
/// );
///
/// final result = await verifiedAsk('Was Li Bai an emperor?');
/// ```
class VerifiedGenerator {
  /// The configuration for verification.
  final FactLiteConfig config;

  /// The underlying LLM generator function.
  final LlmGenerator generator;

  const VerifiedGenerator({required this.config, required this.generator});

  /// Call the verified generator with the given [prompt].
  Future<String> call(String prompt) {
    return verify(prompt: prompt, generator: generator, config: config);
  }
}
