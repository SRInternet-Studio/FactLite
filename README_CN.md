# FactLite 🪶

[English](README.md) | 中文

**只需几行代码，为你的大语言模型（LLM）装上"System 2"大脑。**

[![pub package](https://img.shields.io/pub/v/factlite.svg)](https://pub.dev/packages/factlite)
[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

在部署生成式 AI 的"最后一公里"，**模型幻觉总是最终的大 Boss**。大型框架会引入过多的模板代码和复杂性，而直接调用原始 API 又没有任何安全保障。

**FactLite** 是一个为生产环境而生的、超轻量级的 Dart/Flutter 包，专为解决这一痛点而设计。它从顶级的 **"智能体（Agentic）Reflexion"架构** 中汲取灵感，通过一个自动化的、自我修正的评估循环来增强你现有的 LLM 调用，而无需你重构代码库。

## 🚀 核心特性

*   **✨ 零侵入式设计:** 只需极少的代码改动，就能为任何函数添加事实核查与自我修正能力。完全无需重写你现有的业务逻辑。
*   **⚡️ 原生异步:** 从底层设计上支持 `async/await`。
*   **🤖 智能体工作流:** 实现了一个自动化的 **生成 -> 评估 -> 反思** 循环。你的 LLM 会被迫审视并迭代改进它自己的答案，直到满足你设定的质量标准。
*   **🧩 可扩展 & 插件化:**
    *   **自带"裁判"**: 你可以使用内置的 `LLMJudge`，也可以通过 `CustomJudge` 创建自己的验证逻辑（例如：正则表达式、数据库查询、类型检查）。
    *   **自定义失败策略**: 通过自定义 `FallbackAction`，你可以精确定义失败后的行为——是抛出异常，返回一条安全无害的消息，还是实现自定义逻辑。
*   **🌐 框架无关:** 可与任何 LLM 提供商配合使用 — OpenAI、Anthropic、DeepSeek、本地模型，或任何 OpenAI 兼容的 API。

## 📦 安装

```yaml
# pubspec.yaml
dependencies:
  factlite:
    git:
      url: https://github.com/SRInternet-Studio/FactLite.git
      ref: flutter-package
```

```bash
flutter pub get
```

## 🎯 快速上手：感受"灵光一现"的瞬间

看看为你现有的 LLM 调用添加自我修正能力有多么简单。

**之前：一个标准的、毫无保护的 LLM 调用。**

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<String> askAI(String question) async {
  final response = await http.post(
    Uri.parse('https://api.openai.com/v1/chat/completions'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer 你的密钥',
    },
    body: jsonEncode({
      'model': 'gpt-3.5-turbo',
      'messages': [{'role': 'user', 'content': question}],
    }),
  );
  final body = jsonDecode(response.body);
  return body['choices'][0]['message']['content'];
}

// 这可能会返回一个事实错误的答案，而你永远不会知道。
void main() async {
  print(await askAI('李白是宋朝的皇帝吗？'));
}
```

**之后：受到 FactLite 的保护。**

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:factlite/factlite.dart';

// 一个调用 OpenAI API 的辅助函数（你可以使用任何 SDK 或 HTTP 客户端）
Future<String> chatCompletion(List<Map<String, String>> messages) async {
  final response = await http.post(
    Uri.parse('https://api.openai.com/v1/chat/completions'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer 你的密钥',
    },
    body: jsonEncode({
      'model': 'gpt-4o-mini',
      'messages': messages,
    }),
  );
  final body = jsonDecode(response.body);
  return body['choices'][0]['message']['content'];
}

Future<String> askAI(String question) async {
  final result = await chatCompletion([
    {'role': 'user', 'content': question},
  ]);
  return result;
}

void main() async {
  // 配置一个"裁判" — 只需传入同一个 chatCompletion 函数！
  final config = FactLiteConfig(
    rule: LLMJudge(chatCompletion: chatCompletion),
    maxRetries: 1,
    onFail: ReturnBest(),
  );

  // 调用 verify — 就这么简单！
  final result = await verify(
    prompt: '李白是宋朝的皇帝吗？',
    generator: askAI,
    config: config,
  );

  print(result);
}
```

**你将在控制台看到如下输出：**

```text
[FactLite] Generating initial answer...
[FactLite] Evaluating answer quality...
[FactLite] ❌ Hallucination or error detected: The answer incorrectly states...
[FactLite] Triggering reflection and rewrite, attempt 1...
[FactLite] Evaluating answer quality...
[FactLite] ✅ Correction successful, returning the verified answer!
```

## 💡 高级用法

### VerifiedGenerator

使用 `VerifiedGenerator` 创建一个可复用的验证函数，非常适合将配置一次性绑定到生成器函数，然后在整个应用中使用。

```dart
final verifiedAsk = VerifiedGenerator(
  config: FactLiteConfig(
    rule: LLMJudge(chatCompletion: chatCompletion),
    maxRetries: 2,
  ),
  generator: askAI,
);

// 像函数一样使用它
final result = await verifiedAsk('给我讲讲唐朝的历史。');
print(result);
```

### 联网增强验证 (`WebLLMJudge`)

利用网络搜索来验证答案是否符合最新信息，非常适合时效性强或快速变化的话题。

```dart
// 提供你自己的网络搜索实现
Future<List<String>> myWebSearch(String query) async {
  // 使用任何搜索提供商：DuckDuckGo、Bing、Google 等
  final results = await duckDuckGo.search(query, maxResults: 3);
  return results.map((r) => r.body).toList();
}

final config = FactLiteConfig(
  rule: WebLLMJudge(
    chatCompletion: chatCompletion,
    webSearch: myWebSearch,
    maxResults: 3, // 使用的搜索结果数量
  ),
  maxRetries: 1,
  onFail: ReturnBest(),
);

final result = await verify(
  prompt: 'Flutter 的最新版本是什么？',
  generator: askAI,
  config: config,
);
```

**WebLLMJudge 参数说明：**

| 参数              | 类型                      | 必填   | 说明                                              |
|------------------|--------------------------|--------|--------------------------------------------------|
| `chatCompletion` | `ChatCompletionFunction` | ✅     | 用于评估的 LLM 聊天补全函数                          |
| `webSearch`      | `WebSearchFunction`      | ✅     | 网络搜索函数：`(String) => Future<List<String>>`    |
| `maxResults`     | `int`                    | ❌     | 使用的搜索结果数量（默认：3）                         |

### 自定义规则 (`CustomJudge`)

除了基于 LLM 的检查，你还可以强制执行任何你能想到的本地业务逻辑。

```dart
final judge = CustomJudge(
  evalFunc: (String userPrompt, String answer) {
    // 规则1：不允许过短的回答
    if (answer.length < 50) {
      return {'is_pass': false, 'feedback': '回答太短了，请再详细一点。'};
    }
    // 规则2：不能提及竞争对手
    if (answer.contains('谷歌')) {
      return {'is_pass': false, 'feedback': '请不要提及竞争对手的名字。'};
    }
    return {'is_pass': true, 'feedback': ''};
  },
);

final result = await verify(
  prompt: '介绍一下我们的产品。',
  generator: askAI,
  rule: judge,
);
```

`CustomJudge` 也支持异步评估函数：

```dart
final asyncJudge = CustomJudge(
  evalFunc: (String userPrompt, String answer) async {
    // 例如：对比数据库校验
    final isValid = await checkDatabase(answer);
    return {
      'is_pass': isValid,
      'feedback': isValid ? '' : '答案未在已验证的数据库中找到。',
    };
  },
);
```

### 自定义失败兜底操作 (`FallbackAction`)

当一个答案在所有重试后仍然失败时，精确定义接下来会发生什么。

```dart
// 返回一条安全消息
final result = await verify(
  prompt: '敏感问题',
  generator: askAI,
  rule: myRule,
  onFail: ReturnSafeMessage(safeMessage: '很抱歉，我现在无法对该问题提供一个确切的答案。'),
);

// 抛出异常（抛出 FactLiteVerificationException）
final result = await verify(
  prompt: '关键问题',
  generator: askAI,
  rule: myRule,
  onFail: RaiseError(),
);

// 即使失败也返回最后一个答案（默认行为）
final result = await verify(
  prompt: '一般问题',
  generator: askAI,
  rule: myRule,
  onFail: ReturnBest(),
);
```

你也可以实现自己的 `FallbackAction`：

```dart
class LogAndReturnAction extends FallbackAction {
  @override
  Future<String> execute({
    required String prompt,
    required String lastAnswer,
    required String feedback,
  }) async {
    // 记录到你的分析服务
    await analyticsService.logFailure(prompt, feedback);
    return lastAnswer;
  }
}
```

## 🛠️ 工作原理

FactLite 将你的 LLM 调用包装在一个简单而强大的控制循环中：

1.  **生成 (Generate)**: 调用你的生成器函数以生成一个初步的答案草稿。
2.  **评估 (Evaluate)**: 调用配置好的 `rule` (例如 `LLMJudge`) 来评估草稿的质量。
3.  **反思与重试 (Reflect & Retry)**:
    *   如果评估通过，答案将直接返回。
    *   如果评估失败，反馈意见会与原始提示词结合，形成一个"反思提示词"，迫使 LLM 纠正自己的错误。然后从第 1 步重新开始，直到达到 `maxRetries` 上限。
4.  **兜底 (Fallback)**: 如果所有重试都失败了，将执行配置好的 `onFail` 兜底操作。

## 📋 API 参考

### `verify()`

核心验证函数。

| 参数         | 类型               | 必填   | 说明                                            |
|-------------|-------------------|--------|------------------------------------------------|
| `prompt`    | `String`          | ✅     | 用户的原始问题                                    |
| `generator` | `LlmGenerator`    | ✅     | 异步函数：`(String) => Future<String>`            |
| `rule`      | `BaseRule`         | ❌*    | 用于评估答案的"裁判"                               |
| `maxRetries`| `int`              | ❌     | 最大重试次数（默认：2）                             |
| `onFail`    | `FallbackAction`   | ❌     | 兜底策略（默认：`ReturnBest()`）                    |
| `config`    | `FactLiteConfig`   | ❌*    | 配置对象（会覆盖单独设置的参数）                      |

*`rule` 和 `config` 必须至少提供其一。

### 类

| 类                              | 说明                                              |
|--------------------------------|---------------------------------------------------|
| `LLMJudge`                    | 接受用户提供的 `ChatCompletionFunction`，通过任何 LLM 评估答案 |
| `WebLLMJudge`                 | 联网增强"裁判"，使用搜索结果 + LLM 进行验证              |
| `CustomJudge`                  | 使用自定义函数进行评估                                |
| `FactLiteConfig`               | 将规则、重试次数和兜底策略组合为一个配置对象              |
| `VerifiedGenerator`            | 可复用的包装器，将配置绑定到生成器函数                    |
| `ReturnBest`                   | 即使失败也返回最后一个答案                             |
| `RaiseError`                   | 抛出 `FactLiteVerificationException` 异常           |
| `ReturnSafeMessage`            | 返回一条可配置的安全消息                               |
| `EvaluationResult`             | 规则评估结果（`isPass`、`feedback`）                  |
| `FactLiteVerificationException`| `RaiseError` 抛出的异常类型                          |

## 🤝 贡献

欢迎参与贡献！无论是提交一个新的规则、一个新的兜底操作，还是一个性能改进，都欢迎你提出 Issue 或提交 Pull Request。

## 📄 许可证

本项目基于 MIT 许可证。详情请参阅 `LICENSE` 文件。
