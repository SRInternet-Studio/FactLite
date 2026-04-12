# FactLite 🪶

English | [中文](README_CN.md)

**Give Your LLM a "System 2" Brain with a Single Decorator.**

<img width="1269" height="540" alt="Poster" src="https://github.com/user-attachments/assets/14d4fb29-4007-40bd-9c8e-83aacd04988f" />

[![PyPI version](https://badge.fury.io/py/FactLite.svg)](https://badge.fury.io/py/FactLite)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)

---

In the last mile of deploying Generative AI, **hallucination is the final boss**. Heavy frameworks like LangChain introduce too much boilerplate and complexity, while raw API calls offer no safety net.

**FactLite** is a production-ready, feather-light Python micro-framework designed to solve this exact problem. It enhances your existing LLM calls with an automated, self-correcting evaluation loop, inspired by the top-tier **Agentic "Reflexion" Architecture**, without forcing you to refactor your codebase.

## 🚀 Key Features

*   **✨ Zero-Intrusion:** Add fact-checking and self-correction to any function with a single `@verify` decorator. No need to rewrite your existing logic.
*   **⚡️ Async-Native & Concurrency Safe:** Built from the ground up to support `async/await`. The evaluation process runs in a separate thread to prevent blocking your main event loop, making it perfect for high-performance web backends like FastAPI.
*   **🤖 Agentic Workflow:** Implements an automated **Generate -> Evaluate -> Reflect** loop. Your LLM is forced to critique and iteratively improve its own answers until they meet your quality standards.
*   **🧩 Extensible & Pluggable:**
    *   Bring your own judge! Use the built-in `LLMJudge` or create your own validation logic (e.g., regex, database lookups, type checks) with `CustomJudge`.
    *   Define your own failure policies. Raise an error, return a safe message, or trigger a webhook with custom `FallbackAction`.
*   **🌐 Framework Agnostic:** FactLite doesn't care how you call your LLM. Whether you're using the `openai` SDK, `anthropic`'s client, or a simple `requests.post` call to a local model, as long as it's a Python function that returns a string, FactLite can safeguard it.

## 📦 Installation

```bash
pip install FactLite==1.1.0.post1
```

## 🎯 Quick Start: The "Aha!" Moment

See how easy it is to upgrade your existing code from a simple API call to a self-correcting agent.

**Before: A standard, unprotected LLM call.**

```python
import openai

client = openai.OpenAI(api_key="your-key")

def ask_ai(question: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

# This might return a factually incorrect answer, and you'd never know.
print(ask_ai("Was Li Bai an emperor in the Song Dynasty?"))
```

**After: Protected by FactLite with a single line of code.**

```python
import openai
from FactLite import verify, rules, action

client = openai.OpenAI(api_key="your-key")

# Configure a powerful judge and your API key
config = verify.config(
    rule=rules.LLMJudge(model="gpt-4o-mini", api_key="your-key"),
    max_retries=1
)

@verify(config=config, user_prompt="question") # Just add this decorator!
def ask_ai(question: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

# Now, the function will automatically correct itself before returning.
print(ask_ai("Was Li Bai an emperor in the Song Dynasty?"))
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

### Async Support

FactLite automatically detects and supports `async` functions.

```python
from openai import AsyncOpenAI

async_client = AsyncOpenAI(api_key="your-key")

@verify(config=config, user_prompt="question")
async def ask_ai_async(question: str):
    response = await async_client.chat.completions.create(...)
    return response.choices[0].message.content

# Run it
import asyncio
asyncio.run(ask_ai_async("Tell me about the Tang Dynasty."))
```

### Custom Rules (`CustomJudge`)

Go beyond LLM-based checks. Enforce any local business logic you can imagine.

```python
def company_policy_judge(prompt, answer):
    # Rule 1: No short answers
    if len(answer) < 50:
        return {"is_pass": False, "feedback": "Answer is too short. Please be more detailed."}
    # Rule 2: Don't mention competitors
    if "Google" in answer:
        return {"is_pass": False, "feedback": "Do not mention competitor names."}
    return {"is_pass": True, "feedback": ""}

@verify(rule=rules.CustomJudge(eval_func=company_policy_judge), user_prompt="prompt")
def ask_support_bot(prompt: str):
    # ... your LLM call
    pass
```

### Web-Enhanced Verification (`Web_LLMJudge`)

Leverage web search to verify answers against the latest information, perfect for time-sensitive or rapidly evolving topics.

```python
@verify(
    rule=rules.Web_LLMJudge(
        model="gpt-4o-mini",
        max_results=3,  # Number of search results to use
        backend="duckduckgo"  # Search backend
    ),
    user_prompt="question"
)
def ask_ai_about_current_events(question: str):
    # ... your LLM call
    pass
```

**Web_LLMJudge Parameters:**
- `model`: The OpenAI model to use for evaluation
- `max_results`: Number of search results to incorporate (default: 3)
- `backend`: Search backend, supports "duckduckgo", "bing", "google" (default: "duckduckgo")
- `proxy`: Optional proxy for web search
- `api_key`: Optional OpenAI API key (defaults to global `openai.api_key`)
- `base_url`: Optional OpenAI API base URL

### Custom Failure Actions (`FallbackAction`)

Decide exactly what happens when an answer fails all retries.

```python
from FactLite import action

@verify(
    ...,
    on_fail=action.ReturnSafeMessage("I'm sorry, I cannot provide a confident answer to that question at the moment.")
)
def ask_sensitive_question(...):
    pass

@verify(..., on_fail=action.RaiseError())
def ask_critical_question(...):
    pass
```

## 🛠️ How It Works

FactLite's `@verify` decorator wraps your function in a simple yet powerful control loop:

1.  **Generate**: Your original function is called to produce an initial draft.
2.  **Evaluate**: The configured `rule` (e.g., `LLMJudge`) is invoked to assess the draft.
3.  **Reflect & Retry**:
    *   If the evaluation passes, the answer is returned to the user.
    *   If it fails, the feedback is combined with the original prompt to create a "reflection prompt," forcing the LLM to correct its mistake. The process repeats from Step 1 until `max_retries` is reached.
4.  **Fallback**: If all retries fail, the configured `on_fail` action is executed.

## 🤝 Contributing

Contributions are welcome! Whether it's a new rule, a new fallback action, or a performance improvement, feel free to open an issue or submit a pull request.

The cover design for this project was supported by [@apanzinc](https://github.com/apanzinc).

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
