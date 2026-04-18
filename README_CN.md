# FactLite 🪶

[English](README.md) | 中文

**只需一个高阶函数，为你的大语言模型（LLM）装上"System 2"大脑。**

<img width="1269" height="540" alt="Poster" src="https://github.com/user-attachments/assets/14d4fb29-4007-40bd-9c8e-83aacd04988f" />

[![npm version](https://badge.fury.io/js/factlite.svg)](https://badge.fury.io/js/factlite)
[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

---

在部署生成式 AI 的"最后一公里"，**模型幻觉总是最终的大 Boss**。大型框架会引入过多的模板代码和复杂性，而直接调用原始 API 又没有任何安全保障。

**FactLite** 是一个为生产环境而生的、超轻量级的 Node.js 微框架，专为解决这一痛点而设计。它从顶级的 **"智能体（Agentic）Reflexion"架构** 中汲取灵感，通过一个自动化的、自我修正的评估循环来增强你现有的 LLM 调用，而无需你重构代码库。

## 🚀 核心特性

*   **✨ 零侵入式设计:** 只需用 `verify()` 高阶函数包裹你的异步函数，就能添加事实核查与自我修正能力。完全无需重写现有的业务逻辑。
*   **⚡️ 原生异步:** 从底层设计上就支持 `async/await`，完美适用于 Express、Fastify、Koa 等高性能 Node.js 后端。
*   **🤖 智能体工作流:** 实现了一个自动化的 **生成 -> 评估 -> 反思** 循环。你的 LLM 会被迫审视并迭代改进它自己的答案，直到满足你设定的质量标准。
*   **🧩 可扩展 & 插件化:**
    *   **自带"裁判"**: 你可以使用内置的 `LLMJudge`，也可以通过 `CustomJudge` 创建自己的验证逻辑（例如：正则表达式、数据库查询、类型检查）。
    *   **自定义失败策略**: 通过自定义 `FallbackAction`，你可以精确定义失败后的行为——是抛出异常，返回一条安全无害的消息，还是执行自定义逻辑。
*   **🌐 框架无关:** FactLite 不关心你如何调用 LLM。无论你用的是 `openai` 的 SDK、`anthropic` 的客户端，还是一个简单的 `fetch` 去调用本地模型，只要它是一个返回字符串的异步函数，FactLite 就能为它保驾护航。

## 📦 安装

```bash
npm install "git+https://github.com/SRInternet-Studio/FactLite.git#nodejs-package"
#or
npm install factlite
```

## 🎯 快速上手：感受"灵光一现"的瞬间

看看将你的代码从一个普通的 API 调用升级为一个能自我修正的智能体有多么简单。

**之前：一个标准的、毫无保护的 LLM 调用。**

```javascript
import OpenAI from "openai";

const client = new OpenAI({ apiKey: "你的密钥" });

async function askAI(question) {
  const response = await client.chat.completions.create({
    model: "gpt-3.5-turbo",
    messages: [{ role: "user", content: question }],
  });
  return response.choices[0].message.content;
}

// 这可能会返回一个事实错误的答案，而你永远不会知道。
console.log(await askAI("李白是宋朝的皇帝吗？"));
```

**之后：只需用 FactLite 包裹一下，即可获得保护。**

```javascript
import OpenAI from "openai";
import { verify, rules, actions } from "factlite";

const client = new OpenAI({ apiKey: "你的密钥" });

// 配置一个强大的"裁判"
const config = verify.config({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "你的密钥" }),
  maxRetries: 1,
});

// 用 verify 包裹你的函数
const askAI = verify({ config })(async function (question) {
  const response = await client.chat.completions.create({
    model: "gpt-3.5-turbo",
    messages: [{ role: "user", content: question }],
  });
  return response.choices[0].message.content;
});

// 现在，函数会在返回结果前自动修正答案。
console.log(await askAI("李白是宋朝的皇帝吗？"));
```

**你将在控制台看到如下输出：**

```text
10:30:05 - [FactLite] - Generating initial answer...
10:30:08 - [FactLite] - Evaluating answer quality...
10:30:12 - [FactLite] - ❌ Hallucination or error detected: The answer incorrectly states that Li Bai was related to the Song Dynasty. He was a poet from the Tang Dynasty.
10:30:12 - [FactLite] - Triggering reflection and rewrite, attempt 1...
10:30:16 - [FactLite] - Evaluating answer quality...
10:30:19 - [FactLite] - ✅ Correction successful, returning the verified answer!

不，李白不是宋朝的皇帝。他是一位生活在唐朝（公元701-762年）的著名诗人。
```

## 💡 高级用法

### 自定义规则 (`CustomJudge`)

除了基于 LLM 的检查，你还可以强制执行任何你能想到的本地业务逻辑。

```javascript
function companyPolicyJudge(prompt, answer) {
  // 规则1：不允许过短的回答
  if (answer.length < 50) {
    return { is_pass: false, feedback: "回答太短了，请再详细一点。" };
  }
  // 规则2：不能提及竞争对手
  if (answer.includes("谷歌")) {
    return { is_pass: false, feedback: "请不要提及竞争对手的名字。" };
  }
  return { is_pass: true, feedback: "" };
}

const askSupportBot = verify({
  rule: new rules.CustomJudge(companyPolicyJudge),
})(async function (prompt) {
  // ... 你的 LLM 调用逻辑
});
```

### 联网增强验证 (`Web_LLMJudge`)

利用网络搜索来验证答案是否符合最新信息，非常适合时效性强或快速变化的话题。

```javascript
const askAboutCurrentEvents = verify({
  rule: new rules.Web_LLMJudge({
    model: "gpt-4o-mini",
    maxResults: 3,      // 使用的搜索结果数量
    apiKey: "你的密钥",
  }),
})(async function (question) {
  // ... 你的 LLM 调用逻辑
});
```

**Web_LLMJudge 参数说明：**
- `model`：用于评估的 OpenAI 模型
- `maxResults`：使用的搜索结果数量（默认：3）
- `apiKey`：可选的 OpenAI API 密钥
- `baseURL`：可选的 OpenAI API 基础 URL

### 自定义失败兜底操作 (`FallbackAction`)

当一个答案在所有重试后仍然失败时，精确定义接下来会发生什么。

```javascript
import { actions } from "factlite";

const askSensitiveQuestion = verify({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "你的密钥" }),
  onFail: new actions.ReturnSafeMessage("很抱歉，我现在无法对该问题提供一个确切的答案。"),
})(async function (question) {
  // ... 你的 LLM 调用逻辑
});

const askCriticalQuestion = verify({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "你的密钥" }),
  onFail: new actions.RaiseError(),
})(async function (question) {
  // ... 你的 LLM 调用逻辑
});
```

### 使用 Config 对象

将配置归组到一个可复用的 `Config` 对象中：

```javascript
const config = verify.config({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "你的密钥" }),
  maxRetries: 2,
  onFail: new actions.ReturnBest(),
});

const fn1 = verify({ config })(async (q) => { /* ... */ });
const fn2 = verify({ config })(async (q) => { /* ... */ });
```

## 🛠️ 工作原理

FactLite 的 `verify()` 高阶函数将你的异步函数包装在一个简单而强大的控制循环中：

1.  **生成 (Generate)**: 调用你的原始函数以生成一个初步的答案草稿。
2.  **评估 (Evaluate)**: 调用配置好的 `rule` (例如 `LLMJudge`) 来评估草稿的质量。
3.  **反思与重试 (Reflect & Retry)**:
    *   如果评估通过，答案将直接返回给调用者。
    *   如果评估失败，反馈意见会与原始提示词结合，形成一个"反思提示词"，迫使 LLM 纠正自己的错误。然后从第 1 步重新开始，直到达到 `maxRetries` 上限。
4.  **兜底 (Fallback)**: 如果所有重试都失败了，将执行配置好的 `onFail` 兜底操作。

## 🤝 贡献

欢迎参与贡献！无论是提交一个新的规则、一个新的兜底操作，还是一个性能改进，都欢迎你提出 Issue 或提交 Pull Request。

本项目的封面设计由 [@apanzinc](https://github.com/apanzinc) 提供支持。

## 📄 许可证

本项目基于 MIT 许可证。详情请参阅 `LICENSE` 文件。
