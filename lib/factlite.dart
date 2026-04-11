/// FactLite - A feather-light Dart/Flutter framework for LLM fact-checking
/// and self-correction.
///
/// Give your LLM a "System 2" brain with a simple function wrapper.
///
/// ## Quick Start
///
/// ```dart
/// import 'package:factlite/factlite.dart';
///
/// final config = FactLiteConfig(
///   rule: LLMJudge(
///     chatCompletion: (messages) async {
///       // Use your preferred LLM SDK or HTTP client here
///       return await yourOpenAIClient.chatCompletion(messages);
///     },
///   ),
///   maxRetries: 2,
///   onFail: ReturnBest(),
/// );
///
/// final result = await verify(
///   prompt: 'Was Li Bai an emperor in the Song Dynasty?',
///   generator: (prompt) async {
///     // Your LLM API call here
///     return await callOpenAI(prompt);
///   },
///   config: config,
/// );
/// ```
library;

// Actions - Fallback strategies
export 'src/actions.dart'
    show
        FallbackAction,
        ReturnBest,
        RaiseError,
        ReturnSafeMessage,
        FactLiteVerificationException,
        EvaluationResult;

// Rules - Judge implementations
export 'src/rules.dart'
    show BaseRule, LLMJudge, CustomJudge, EvalFunction, ChatCompletionFunction;

// Config
export 'src/config.dart' show FactLiteConfig;

// Verify - Core verification logic
export 'src/verify.dart' show verify, VerifiedGenerator, LlmGenerator;
