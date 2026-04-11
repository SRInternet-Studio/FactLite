import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
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

/// A judge that uses an LLM (OpenAI-compatible API) to evaluate answers.
///
/// Sends the user prompt and answer to a specified model and expects
/// a JSON response with `is_pass` and `feedback` fields.
class LLMJudge extends BaseRule {
  /// The model to use for evaluation (e.g., "gpt-4o-mini").
  final String model;

  /// The API key for authentication.
  final String apiKey;

  /// The base URL of the OpenAI-compatible API.
  final String baseUrl;

  /// Optional custom HTTP client for testing.
  final http.Client? httpClient;

  LLMJudge({
    this.model = 'gpt-4o-mini',
    required this.apiKey,
    this.baseUrl = 'https://api.openai.com/v1',
    this.httpClient,
  });

  @override
  Future<EvaluationResult> evaluate(String userPrompt, String answer) async {
    final evaluationPrompt = '''You are a fact-checking judge. Evaluate the following response to determine if it accurately answers the user's question. Return a JSON object with two fields:
- is_pass: boolean indicating if the response is factually correct
- feedback: detailed criticism if is_pass is false, or empty string if true

User question: $userPrompt
Response: $answer

JSON output:''';

    try {
      final client = httpClient ?? http.Client();
      final shouldCloseClient = httpClient == null;

      try {
        final url = Uri.parse('$baseUrl/chat/completions');
        final response = await client.post(
          url,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $apiKey',
          },
          body: jsonEncode({
            'model': model,
            'messages': [
              {
                'role': 'system',
                'content':
                    'You are a fact-checking judge. Return only JSON output.',
              },
              {
                'role': 'user',
                'content': evaluationPrompt,
              },
            ],
            'response_format': {'type': 'json_object'},
          }),
        );

        if (response.statusCode != 200) {
          final errorMessage =
              'LLMJudge API call failed with status ${response.statusCode}: ${response.body}';
          _logger.severe(errorMessage);
          return EvaluationResult(
            isPass: false,
            feedback: errorMessage,
          );
        }

        final responseBody = jsonDecode(response.body) as Map<String, dynamic>;
        final resultStr =
            responseBody['choices'][0]['message']['content'] as String;
        final result = jsonDecode(resultStr) as Map<String, dynamic>;

        return EvaluationResult.fromMap(result);
      } finally {
        if (shouldCloseClient) {
          client.close();
        }
      }
    } catch (e) {
      final errorMessage =
          'LLMJudge API call failed: $e. Please check your API key and network connection.';
      _logger.severe(errorMessage);
      return EvaluationResult(
        isPass: false,
        feedback: errorMessage,
      );
    }
  }
}

/// Type definition for custom evaluation functions.
///
/// The function should take [userPrompt] and [answer] as parameters
/// and return a [Map] with `is_pass` (bool) and `feedback` (String) keys.
///
/// The function can be synchronous or asynchronous (returning a [Future]).
typedef EvalFunction = FutureOr<Map<String, dynamic>> Function(
    String userPrompt, String answer);

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
