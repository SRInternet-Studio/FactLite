# FactLite 🪶

English | [中文](README_CN.md)

**Give Your LLM a "System 2" Brain with a Simple Function Wrapper.**

[![pub package](https://img.shields.io/pub/v/factlite.svg)](https://pub.dev/packages/factlite)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

In the last mile of deploying Generative AI, **hallucination is the final boss**. Heavy frameworks introduce too much boilerplate and complexity, while raw API calls offer no safety net.

**FactLite** is a production-ready, feather-light Dart/Flutter package designed to solve this exact problem. It enhances your existing LLM calls with an automated, self-correcting evaluation loop, inspired by the top-tier **Agentic "Reflexion" Architecture**, without forcing you to refactor your codebase.

## 🚀 Key Features

*   **✨ Zero-Intrusion:** Add fact-checking and self-correction with minimal code changes. No need to rewrite your existing logic.
*   **⚡️ Async-Native:** Built from the ground up to support `async/await`.
*   **🤖 Agentic Workflow:** Implements an automated **Generate -> Evaluate -> Reflect** loop. Your LLM is forced to critique and iteratively improve its own answers until they meet your quality standards.
*   **🧩 Extensible & Pluggable:**
    *   Bring your own judge! Use the built-in `LLMJudge` or create your own validation logic (e.g., regex, database lookups, type checks) with `CustomJudge`.
    *   Define your own failure policies. Raise an error, return a safe message, or implement custom `FallbackAction`.
*   **🌐 Framework Agnostic:** Works with any LLM provider — OpenAI, Anthropic, DeepSeek, local models, or any OpenAI-compatible API.

## 📦 Installation

```yaml
# pubspec.yaml
dependencies:
  factlite: ^0.0.1
```

```bash
flutter pub get
```

## 🎯 Quick Start: The "Aha!" Moment

See how easy it is to add self-correcting capabilities to your existing LLM calls.

**Before: A standard, unprotected LLM call.**

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<String> askAI(String question) async {
  final response = await http.post(
    Uri.parse('https://api.openai.com/v1/chat/completions'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer your-key',
    },
    body: jsonEncode({
      'model': 'gpt-3.5-turbo',
      'messages': [{'role': 'user', 'content': question}],
    }),
  );
  final body = jsonDecode(response.body);
  return body['choices'][0]['message']['content'];
}

// This might return a factually incorrect answer, and you'd never know.
void main() async {
  print(await askAI('Was Li Bai an emperor in the Song Dynasty?'));
}
```

**After: Protected by FactLite.**

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:factlite/factlite.dart';

Future<String> askAI(String question) async {
  final response = await http.post(
    Uri.parse('https://api.openai.com/v1/chat/completions'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer your-key',
    },
    body: jsonEncode({
      'model': 'gpt-3.5-turbo',
      'messages': [{'role': 'user', 'content': question}],
    }),
  );
  final body = jsonDecode(response.body);
  return body['choices'][0]['message']['content'];
}

void main() async {
  // Configure a judge
  final config = FactLiteConfig(
    rule: LLMJudge(apiKey: 'your-key', model: 'gpt-4o-mini'),
    maxRetries: 1,
    onFail: ReturnBest(),
  );

  // Call verify — that's it!
  final result = await verify(
    prompt: 'Was Li Bai an emperor in the Song Dynasty?',
    generator: askAI,
    config: config,
  );

  print(result);
}
```

**What you'll see in your console:**

```text
[FactLite] Generating initial answer...
[FactLite] Evaluating answer quality...
[FactLite] ❌ Hallucination or error detected: The answer incorrectly states...
[FactLite] Triggering reflection and rewrite, attempt 1...
[FactLite] Evaluating answer quality...
[FactLite] ✅ Correction successful, returning the verified answer!
```

## 💡 Advanced Usage

### VerifiedGenerator

Use `VerifiedGenerator` to create a reusable verified function, perfect for binding a configuration to a generator once and using it throughout your app.

```dart
final verifiedAsk = VerifiedGenerator(
  config: FactLiteConfig(
    rule: LLMJudge(apiKey: 'your-key', model: 'gpt-4o-mini'),
    maxRetries: 2,
  ),
  generator: askAI,
);

// Use it like a function
final result = await verifiedAsk('Tell me about the Tang Dynasty.');
print(result);
```

### Custom Rules (`CustomJudge`)

Go beyond LLM-based checks. Enforce any local business logic you can imagine.

```dart
final judge = CustomJudge(
  evalFunc: (String userPrompt, String answer) {
    // Rule 1: No short answers
    if (answer.length < 50) {
      return {'is_pass': false, 'feedback': 'Answer is too short.'};
    }
    // Rule 2: Don't mention competitors
    if (answer.contains('Google')) {
      return {'is_pass': false, 'feedback': 'Do not mention competitor names.'};
    }
    return {'is_pass': true, 'feedback': ''};
  },
);

final result = await verify(
  prompt: 'Tell me about our product.',
  generator: askAI,
  rule: judge,
);
```

`CustomJudge` also supports async evaluation functions:

```dart
final asyncJudge = CustomJudge(
  evalFunc: (String userPrompt, String answer) async {
    // e.g., check against a database
    final isValid = await checkDatabase(answer);
    return {
      'is_pass': isValid,
      'feedback': isValid ? '' : 'Answer not found in verified database.',
    };
  },
);
```

### Custom Failure Actions (`FallbackAction`)

Decide exactly what happens when an answer fails all retries.

```dart
// Return a safe message
final result = await verify(
  prompt: 'Sensitive question',
  generator: askAI,
  rule: myRule,
  onFail: ReturnSafeMessage(safeMessage: 'Sorry, I cannot answer that.'),
);

// Raise an error (throws FactLiteVerificationException)
final result = await verify(
  prompt: 'Critical question',
  generator: askAI,
  rule: myRule,
  onFail: RaiseError(),
);

// Return the last answer despite failure (default behavior)
final result = await verify(
  prompt: 'General question',
  generator: askAI,
  rule: myRule,
  onFail: ReturnBest(),
);
```

You can also implement your own `FallbackAction`:

```dart
class LogAndReturnAction extends FallbackAction {
  @override
  Future<String> execute({
    required String prompt,
    required String lastAnswer,
    required String feedback,
  }) async {
    // Log to your analytics service
    await analyticsService.logFailure(prompt, feedback);
    return lastAnswer;
  }
}
```

## 🛠️ How It Works

FactLite wraps your LLM call in a simple yet powerful control loop:

1.  **Generate**: Your generator function is called to produce an initial draft.
2.  **Evaluate**: The configured `rule` (e.g., `LLMJudge`) is invoked to assess the draft.
3.  **Reflect & Retry**:
    *   If the evaluation passes, the answer is returned immediately.
    *   If it fails, the feedback is combined with the original prompt to create a "reflection prompt," forcing the LLM to correct its mistake. The process repeats from Step 1 until `maxRetries` is reached.
4.  **Fallback**: If all retries fail, the configured `onFail` action is executed.

## 📋 API Reference

### `verify()`

The core function for verified LLM calls.

| Parameter   | Type              | Required | Description                                      |
|-------------|-------------------|----------|--------------------------------------------------|
| `prompt`    | `String`          | ✅       | The original user question                       |
| `generator` | `LlmGenerator`    | ✅       | Async function: `(String) => Future<String>`     |
| `rule`      | `BaseRule`         | ❌*      | The judge to evaluate answers                    |
| `maxRetries`| `int`              | ❌       | Max retry attempts (default: 2)                  |
| `onFail`    | `FallbackAction`   | ❌       | Fallback strategy (default: `ReturnBest()`)      |
| `config`    | `FactLiteConfig`   | ❌*      | Config object (overrides individual params)      |

*Either `rule` or `config` must be provided.

### Classes

| Class                          | Description                                           |
|--------------------------------|-------------------------------------------------------|
| `LLMJudge`                    | Uses an OpenAI-compatible LLM API to evaluate answers |
| `CustomJudge`                  | Uses a custom function for evaluation                 |
| `FactLiteConfig`               | Groups rule, retries, and fallback into one object    |
| `VerifiedGenerator`            | Reusable wrapper binding config to a generator        |
| `ReturnBest`                   | Returns the last answer despite failure               |
| `RaiseError`                   | Throws `FactLiteVerificationException`                |
| `ReturnSafeMessage`            | Returns a configurable safe message                   |
| `EvaluationResult`             | Result of a rule evaluation (`isPass`, `feedback`)    |
| `FactLiteVerificationException`| Exception thrown by `RaiseError`                      |

## 🤝 Contributing

Contributions are welcome! Whether it's a new rule, a new fallback action, or a performance improvement, feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
