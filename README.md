# FactLite 🪶

English | [中文](README_CN.md)

**Give Your LLM a "System 2" Brain with a Simple Higher-Order Function.**

<img width="1269" height="540" alt="Poster" src="https://github.com/user-attachments/assets/14d4fb29-4007-40bd-9c8e-83aacd04988f" />

[![npm version](https://badge.fury.io/js/factlite.svg)](https://badge.fury.io/js/factlite)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

---

In the last mile of deploying Generative AI, **hallucination is the final boss**. Heavy frameworks introduce too much boilerplate and complexity, while raw API calls offer no safety net.

**FactLite** is a production-ready, feather-light Node.js micro-framework designed to solve this exact problem. It enhances your existing LLM calls with an automated, self-correcting evaluation loop, inspired by the top-tier **Agentic "Reflexion" Architecture**, without forcing you to refactor your codebase.

## 🚀 Key Features

*   **✨ Zero-Intrusion:** Add fact-checking and self-correction to any async function with a simple `verify()` higher-order function wrapper. No need to rewrite your existing logic.
*   **⚡️ Async-Native:** Built from the ground up to support `async/await`, making it perfect for high-performance Node.js backends like Express, Fastify, or Koa.
*   **🤖 Agentic Workflow:** Implements an automated **Generate -> Evaluate -> Reflect** loop. Your LLM is forced to critique and iteratively improve its own answers until they meet your quality standards.
*   **🧩 Extensible & Pluggable:**
    *   Bring your own judge! Use the built-in `LLMJudge` or create your own validation logic (e.g., regex, database lookups, type checks) with `CustomJudge`.
    *   Define your own failure policies. Raise an error, return a safe message, or implement custom logic with `FallbackAction`.
*   **🌐 Framework Agnostic:** FactLite doesn't care how you call your LLM. Whether you're using the `openai` SDK, `anthropic`'s client, or a simple `fetch` call to a local model, as long as it's an async function that returns a string, FactLite can safeguard it.

## 📦 Installation

```bash
npm install "git+https://github.com/SRInternet-Studio/FactLite.git#nodejs-package"
#or
npm install factlite
```

## 🎯 Quick Start: The "Aha!" Moment

See how easy it is to upgrade your existing code from a simple API call to a self-correcting agent.

**Before: A standard, unprotected LLM call.**

```javascript
import OpenAI from "openai";

const client = new OpenAI({ apiKey: "your-key" });

async function askAI(question) {
  const response = await client.chat.completions.create({
    model: "gpt-3.5-turbo",
    messages: [{ role: "user", content: question }],
  });
  return response.choices[0].message.content;
}

// This might return a factually incorrect answer, and you'd never know.
console.log(await askAI("Was Li Bai an emperor in the Song Dynasty?"));
```

**After: Protected by FactLite with a simple wrapper.**

```javascript
import OpenAI from "openai";
import { verify, rules, actions } from "factlite";

const client = new OpenAI({ apiKey: "your-key" });

// Configure a powerful judge
const config = verify.config({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "your-key" }),
  maxRetries: 1,
});

// Wrap your function with verify
const askAI = verify({ config })(async function (question) {
  const response = await client.chat.completions.create({
    model: "gpt-3.5-turbo",
    messages: [{ role: "user", content: question }],
  });
  return response.choices[0].message.content;
});

// Now, the function will automatically correct itself before returning.
console.log(await askAI("Was Li Bai an emperor in the Song Dynasty?"));
```

**What you'll see in your console:**

```text
10:30:05 - [FactLite] - Generating initial answer...
10:30:08 - [FactLite] - Evaluating answer quality...
10:30:12 - [FactLite] - ❌ Hallucination or error detected: The answer incorrectly states that Li Bai was related to the Song Dynasty. He was a poet from the Tang Dynasty.
10:30:12 - [FactLite] - Triggering reflection and rewrite, attempt 1...
10:30:16 - [FactLite] - Evaluating answer quality...
10:30:19 - [FactLite] - ✅ Correction successful, returning the verified answer!

No, Li Bai was not an emperor in the Song Dynasty. He was a renowned poet who lived during the Tang Dynasty (701-762 AD).
```

## 💡 Advanced Usage

### Custom Rules (`CustomJudge`)

Go beyond LLM-based checks. Enforce any local business logic you can imagine.

```javascript
function companyPolicyJudge(prompt, answer) {
  // Rule 1: No short answers
  if (answer.length < 50) {
    return { is_pass: false, feedback: "Answer is too short. Please be more detailed." };
  }
  // Rule 2: Don't mention competitors
  if (answer.includes("Google")) {
    return { is_pass: false, feedback: "Do not mention competitor names." };
  }
  return { is_pass: true, feedback: "" };
}

const askSupportBot = verify({
  rule: new rules.CustomJudge(companyPolicyJudge),
})(async function (prompt) {
  // ... your LLM call
});
```

### Web-Enhanced Verification (`Web_LLMJudge`)

Leverage web search to verify answers against the latest information, perfect for time-sensitive or rapidly evolving topics.

```javascript
const askAboutCurrentEvents = verify({
  rule: new rules.Web_LLMJudge({
    model: "gpt-4o-mini",
    maxResults: 3,      // Number of search results to use
    apiKey: "your-key",
  }),
})(async function (question) {
  // ... your LLM call
});
```

**Web_LLMJudge Options:**
- `model`: The OpenAI model to use for evaluation
- `maxResults`: Number of search results to incorporate (default: 3)
- `apiKey`: Optional OpenAI API key
- `baseURL`: Optional OpenAI API base URL

### Custom Failure Actions (`FallbackAction`)

Decide exactly what happens when an answer fails all retries.

```javascript
import { actions } from "factlite";

const askSensitiveQuestion = verify({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "your-key" }),
  onFail: new actions.ReturnSafeMessage(
    "I'm sorry, I cannot provide a confident answer to that question at the moment."
  ),
})(async function (question) {
  // ... your LLM call
});

const askCriticalQuestion = verify({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "your-key" }),
  onFail: new actions.RaiseError(),
})(async function (question) {
  // ... your LLM call
});
```

### Using Config Object

Group your configuration into a reusable `Config` object:

```javascript
const config = verify.config({
  rule: new rules.LLMJudge({ model: "gpt-4o-mini", apiKey: "your-key" }),
  maxRetries: 2,
  onFail: new actions.ReturnBest(),
});

const fn1 = verify({ config })(async (q) => { /* ... */ });
const fn2 = verify({ config })(async (q) => { /* ... */ });
```

## 🛠️ How It Works

FactLite's `verify()` higher-order function wraps your async function in a simple yet powerful control loop:

1.  **Generate**: Your original function is called to produce an initial draft.
2.  **Evaluate**: The configured `rule` (e.g., `LLMJudge`) is invoked to assess the draft.
3.  **Reflect & Retry**:
    *   If the evaluation passes, the answer is returned to the caller.
    *   If it fails, the feedback is combined with the original prompt to create a "reflection prompt," forcing the LLM to correct its mistake. The process repeats from Step 1 until `maxRetries` is reached.
4.  **Fallback**: If all retries fail, the configured `onFail` action is executed.

## 🤝 Contributing

Contributions are welcome! Whether it's a new rule, a new fallback action, or a performance improvement, feel free to open an issue or submit a pull request.

The cover design for this project was supported by [@apanzinc](https://github.com/apanzinc).

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
