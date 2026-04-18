import 'dart:async';
import 'dart:convert';
import 'package:logging/logging.dart';
import 'actions.dart';

final _logger = Logger('FactLite.Rules');

/// Base rule class for all judge implementations.
///
/// Subclasses must implement the [evaluate] method to assess
/// an LLM's answer against the user's prompt.
abstract class BaseRule {
  /// Evaluate the answer against the user prompt.
  ///
  /// [userPrompt] is the original user question.
  /// [answer] is the model's answer.
  ///
  /// Returns an [EvaluationResult] with `isPass` and `feedback`.
  Future<EvaluationResult> evaluate(String userPrompt, String answer);
}

/// Type definition for a chat completion function.
///
/// Takes a list of message maps (each with `role` and `content` keys)
/// and returns the assistant's response content as a [String].
///
/// This allows the user to use any LLM SDK or HTTP client of their choice.
///
/// Example with a hypothetical OpenAI Dart client:
/// ```dart
/// final chatCompletion = (List<Map<String, String>> messages) async {
///   final response = await openai.chat.completions.create(
///     model: 'gpt-4o-mini',
///     messages: messages,
///   );
///   return response.choices.first.message.content;
/// };
/// ```
typedef ChatCompletionFunction =
    Future<String> Function(List<Map<String, String>> messages);

/// A judge that uses an LLM to evaluate answers.
///
/// Instead of managing HTTP requests internally, `LLMJudge` accepts a
/// [ChatCompletionFunction] provided by the user. This means you can use
/// any OpenAI-compatible SDK, HTTP client, or custom implementation.
///
/// Example:
/// ```dart
/// final judge = LLMJudge(
///   chatCompletion: (messages) async {
///     final response = await openai.chat.completions.create(
///       model: 'gpt-4o-mini',
///       messages: messages,
///       responseFormat: {'type': 'json_object'},
///     );
///     return response.choices.first.message.content;
///   },
/// );
/// ```
class LLMJudge extends BaseRule {
  /// The user-provided chat completion function.
  final ChatCompletionFunction chatCompletion;

  LLMJudge({required this.chatCompletion});

  @override
  Future<EvaluationResult> evaluate(String userPrompt, String answer) async {
    final evaluationPrompt =
        '''You are a fact-checking judge. Evaluate the following response to determine if it accurately answers the user's question. Return a JSON object with two fields:
- is_pass: boolean indicating if the response is factually correct
- feedback: detailed criticism if is_pass is false, or empty string if true

User question: $userPrompt
Response: $answer

JSON output:''';

    try {
      final messages = [
        {
          'role': 'system',
          'content': 'You are a fact-checking judge. Return only JSON output.',
        },
        {'role': 'user', 'content': evaluationPrompt},
      ];

      final resultStr = await chatCompletion(messages);
      final result = jsonDecode(resultStr) as Map<String, dynamic>;

      return EvaluationResult.fromMap(result);
    } catch (e) {
      final errorMessage =
          'LLMJudge evaluation failed: $e. Please check your chatCompletion function.';
      _logger.severe(errorMessage);
      return EvaluationResult(isPass: false, feedback: errorMessage);
    }
  }
}

/// Type definition for a web search function.
///
/// Takes a search query string and returns a list of search result snippets.
///
/// This allows the user to use any web search provider or HTTP client of
/// their choice (e.g., DuckDuckGo, Bing, Google, or a custom search API).
///
/// Example with a hypothetical search client:
/// ```dart
/// final webSearch = (String query) async {
///   final results = await duckDuckGo.search(query, maxResults: 3);
///   return results.map((r) => r.body).toList();
/// };
/// ```
typedef WebSearchFunction = Future<List<String>> Function(String query);

/// A judge that uses web search results to enhance LLM-based evaluation.
///
/// `WebLLMJudge` first searches the web for relevant information about the
/// user's question, then uses an LLM to evaluate the answer against both
/// the question and the search results. This is ideal for verifying
/// time-sensitive or rapidly evolving topics.
///
/// Instead of managing HTTP requests or search APIs internally,
/// `WebLLMJudge` accepts both a [ChatCompletionFunction] and a
/// [WebSearchFunction] provided by the user.
///
/// Example:
/// ```dart
/// final judge = WebLLMJudge(
///   chatCompletion: (messages) async {
///     final response = await openai.chat.completions.create(
///       model: 'gpt-4o-mini',
///       messages: messages,
///       responseFormat: {'type': 'json_object'},
///     );
///     return response.choices.first.message.content;
///   },
///   webSearch: (query) async {
///     final results = await duckDuckGo.search(query, maxResults: 3);
///     return results.map((r) => r.body).toList();
///   },
/// );
/// ```
class WebLLMJudge extends BaseRule {
  /// The user-provided chat completion function.
  final ChatCompletionFunction chatCompletion;

  /// The user-provided web search function.
  final WebSearchFunction webSearch;

  /// Maximum number of search results to use for evaluation.
  ///
  /// Defaults to 3.
  final int maxResults;

  WebLLMJudge({
    required this.chatCompletion,
    required this.webSearch,
    this.maxResults = 3,
  });

  @override
  Future<EvaluationResult> evaluate(String userPrompt, String answer) async {
    // Step 1: Web search
    List<String> searchResults;
    try {
      searchResults = await webSearch(userPrompt);
    } catch (e) {
      final errorMessage = 'Error searching the web: $e';
      _logger.severe(errorMessage);
      return EvaluationResult(isPass: false, feedback: errorMessage);
    }

    if (searchResults.isEmpty) {
      return const EvaluationResult(
        isPass: false,
        feedback: 'Can not find any relevant information on the web.',
      );
    }

    // Take only maxResults
    final results = searchResults.take(maxResults).toList();
    final context = results.map((r) => '- $r').join('\n');

    // Step 2: LLM evaluation with web context
    final evaluationPrompt =
        '''You are a fact-checking judge. Please ** use only the [web search] provided below ** to check if the [AI's answer] contains factual errors, fabricated years, or non-existent entities. Return a JSON object with two fields:
- is_pass: boolean indicating if the response is factually correct
- feedback: detailed criticism if is_pass is false, or empty string if true

[web search]
$context

[User question]: $userPrompt
[AI's answer]: $answer

JSON output:''';

    try {
      final messages = [
        {
          'role': 'system',
          'content': 'You are a fact-checking judge. Return only JSON output.',
        },
        {'role': 'user', 'content': evaluationPrompt},
      ];

      final resultStr = await chatCompletion(messages);
      final result = jsonDecode(resultStr) as Map<String, dynamic>;

      return EvaluationResult.fromMap(result);
    } catch (e) {
      final errorMessage =
          'WebLLMJudge evaluation failed: $e. Please check your chatCompletion function.';
      _logger.severe(errorMessage);
      return EvaluationResult(isPass: false, feedback: errorMessage);
    }
  }
}

/// Type definition for custom evaluation functions.
///
/// The function should take [userPrompt] and [answer] as parameters
/// and return a [Map] with `is_pass` (bool) and `feedback` (String) keys.
///
/// The function can be synchronous or asynchronous (returning a [Future]).
typedef EvalFunction =
    FutureOr<Map<String, dynamic>> Function(String userPrompt, String answer);

/// A judge that uses a custom evaluation function.
///
/// This allows you to define arbitrary validation logic such as
/// regex checks, database lookups, keyword filtering, length checks, etc.
///
/// Example:
/// ```dart
/// final judge = CustomJudge(evalFunc: (userPrompt, answer) {
///   if (answer.length < 50) {
///     return {'is_pass': false, 'feedback': 'Answer is too short.'};
///   }
///   return {'is_pass': true, 'feedback': ''};
/// });
/// ```
class CustomJudge extends BaseRule {
  /// The custom evaluation function.
  final Function _evalFunc;

  /// Creates a [CustomJudge] with the given evaluation function.
  ///
  /// The [evalFunc] must accept two parameters: `userPrompt` and `answer`,
  /// and return a `Map<String, dynamic>` (or `Future<Map<String, dynamic>>`)
  /// with `is_pass` (bool) and `feedback` (String) keys.
  CustomJudge({required Function evalFunc}) : _evalFunc = evalFunc;

  @override
  Future<EvaluationResult> evaluate(String userPrompt, String answer) async {
    try {
      // Call the custom evaluation function
      final rawResult = _evalFunc(userPrompt, answer);

      // Handle both sync and async results
      final Map<String, dynamic> result;
      if (rawResult is Future) {
        result = await rawResult as Map<String, dynamic>;
      } else {
        result = rawResult as Map<String, dynamic>;
      }

      // Validate the result
      if (!result.containsKey('is_pass')) {
        throw ArgumentError("Returned map must contain 'is_pass' key");
      }
      if (!result.containsKey('feedback')) {
        throw ArgumentError("Returned map must contain 'feedback' key");
      }
      if (result['is_pass'] is! bool) {
        throw ArgumentError("'is_pass' must be a bool");
      }
      if (result['feedback'] is! String) {
        throw ArgumentError("'feedback' must be a String");
      }

      return EvaluationResult.fromMap(result);
    } catch (e) {
      // Convert any error to a failed evaluation
      return EvaluationResult(
        isPass: false,
        feedback:
            'Error in custom judge: $e. Please fix your evaluation function.',
      );
    }
  }
}
