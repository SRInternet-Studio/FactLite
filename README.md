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
pip install FactLite -i https://pypi.tuna.tsinghua.edu.cn/simple/
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
    rules=rules.LLMJudge(model="gpt-4o-mini", api_key="your-key"),
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

## 📖 More Usage

### Basic Validators

#### Regex Validation (`RegexValidator`)

Use regular expressions to enforce content rules, such as banning specific words or requiring certain patterns.

```python
@verify(
    rules=rules.RegexValidator(
        banned_words=["competitor", "rival", "Google"],
        required_pattern=[r"our product"],
        banned_words_file="path/to/banned_words.txt"
    ),
    user_prompt="prompt"
)
def product_promotion(prompt: str):
    # ... your LLM call
    pass
```

**RegexValidator Parameters:**
- `banned_words`: List of words or phrases to ban
- `required_pattern`: List of regular expression patterns that must be present
- `banned_words_file`: Path to a TXT file containing banned words (one per line)

#### Length Validation (`LengthValidator`)

Ensure the AI response meets length requirements, with optional punctuation exclusion.

```python
@verify(
    rules=rules.LengthValidator(
        min_length=50,
        max_length=500,
        include_punctuation=True
    ),
    user_prompt="prompt"
)
def generate_response(prompt: str):
    # ... your LLM call
    pass
```

**LengthValidator Parameters:**
- `min_length`: Minimum length of the answer
- `max_length`: Maximum length of the answer
- `include_punctuation`: Whether to include punctuation in length calculation (default: True)

#### JSON Validation (`JSONValidator`)

Ensure the LLM returns valid JSON with all required keys.

```python
@verify(
    rules=rules.JSONValidator(
        required_keys=["name", "price", "description"]
    ),
    user_prompt="prompt"
)
def generate_product_json(prompt: str):
    # ... your LLM call
    pass
```

**JSONValidator Parameters:**
- `required_keys`: List of keys that must be present in the JSON output

#### Content Moderation (`ModerationJudge`)

Use OpenAI's Moderation API to detect unsafe content such as hate speech, violence, and adult content.

```python
@verify(
    rules=rules.ModerationJudge(),
    user_prompt="prompt"
)
def generate_content(prompt: str):
    # ... your LLM call
    pass
```

**ModerationJudge Parameters:**
- `api_key`: OpenAI API key (defaults to global `openai.api_key`)

**Detected Categories:**
- `hate`: Content that expresses, incites, or promotes hate based on race, gender, ethnicity, religion, nationality, sexual orientation, disability, or caste
- `hate/threatening`: Content that threatens violence against an individual or group
- `self-harm`: Content that promotes or depicts suicide, self-injury, or eating disorders
- `sexual`: Content that contains adult themes or sexual content
- `sexual/minors`: Content that contains sexual content involving minors
- `violence`: Content that depicts or promotes violence
- `violence/graphic`: Content that depicts extreme or graphic violence

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

@verify(rules=rules.CustomJudge(eval_func=company_policy_judge), user_prompt="prompt")
def ask_support_bot(prompt: str):
    # ... your LLM call
    pass
```

### Web-Enhanced Verification (`Web_LLMJudge`)

Leverage web search to verify answers against the latest information, perfect for time-sensitive or rapidly evolving topics.

```python
@verify(
    rules=rules.Web_LLMJudge(
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

### Rule Chaining

Execute multiple validators sequentially to create complex validation workflows.

```python
@verify(
    rules=[
        rules.RegexValidator(
            banned_words=["competitor", "rival"],
            required_pattern=[r"our product"]
        ),
        rules.LengthValidator(
            min_length=50,
            max_length=500
        ),
        rules.ModerationJudge()
    ],
    user_prompt="prompt"
)
def generate_marketing_content(prompt: str):
    # ... your LLM call
    pass
```

**How Rule Chaining Works:**
1. Validators are executed in the order they appear in the list
2. If any validator fails, the chain stops immediately
3. If a validator returns `no_retry=True`, the entire process stops without retries
4. Only when all validators pass does the answer get returned

**Benefits of Rule Chaining:**
- **Efficiency**: Stop early if any validation fails
- **Flexibility**: Combine different types of validations
- **Modularity**: Reuse validators across different chains
- **Clear Logic**: Easy to understand validation flow

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

## 📊 Benchmark (AA-Omniscience Benchmark)

To rigorously quantify FactLite's ability to mitigate hallucinations, we tested it against the **AA-Omniscience Benchmark**, a notoriously difficult dataset comprising highly specialized domain questions (Finance, Law, Medicine, etc.).

The AA-Omniscience scoring metric heavily penalizes hallucinations: `Omniscience Index (OI) = Correct(%) - Incorrect(%)`. Abstaining from guessing yields 0 penalty.

**Test Setup:**
*   **Model:** DeepSeek V4 Flash
*   **Sample Size:** 201 factual questions (Randomly selected from [the public dataset of AA-Omniscience](https://huggingface.co/datasets/ArtificialAnalysis/AA-Omniscience-Public))
*   **FactLite Config:** `@verify` with `Web_LLMJudge` (backend: `auto`) and `ReturnSafeMessage` fallback.

### 📈 Performance Results

| Metric | Baseline (Raw LLM) | With FactLite | Shift |
| :--- | :--- | :--- | :--- |
| **✅ Correct** | 36.0% | 32.0% | -4.0% |
| **❌ Incorrect/Hallucination** | **63.5%** | **16.0%** | **📉 -47.5%** |
| **🛡️ Abstain/Safe Fallback** | 0.5% | 52.0% | 📈 +51.5% |
| **🏆 Omniscience Index (OI)** | **-27.50** | **+16.00** | **🚀 +43.50 pts** |

You can view the answer results for each question in the [aa_omniscience_eval_report.csv](aa_omniscience_eval_report.csv) test report.

### 🔬 Statistical Significance (P-Value)

To ensure the observed reduction in hallucinations was not due to random chance, we conducted a statistical hypothesis test (**McNemar's Test** for paired nominal data).

*   **Null Hypothesis ($H_0$)**: FactLite has no actual effect on the model's hallucination rate.
*   **Result**: The absolute reduction of 47.5% yielded a Z-score approaching 10.0, resulting in a **$p$-value < 0.0001**.
*   **Verdict**: We reject the null hypothesis with **>99.99% confidence**. The mitigation of hallucinations is highly statistically significant, proving the deterministic effectiveness of the FactLite architecture rather than statistical noise.

**Conclusion:** By intelligently retrieving external facts and enforcing strict "fail-fast" fallbacks when evidence is absent, FactLite successfully intercepted nearly 50% of fatal hallucinations, fundamentally elevating its reliability for production environments.

## 🛠️ How It Works

FactLite's `@verify` decorator wraps your function in a simple yet powerful control loop:

1.  **Generate**: Your original function is called to produce an initial draft.
2.  **Evaluate**: The configured `rules` (e.g., `LLMJudge`) is invoked to assess the draft.
3.  **Reflect & Retry**:
    *   If the evaluation passes, the answer is returned to the user.
    *   If it fails, the feedback is combined with the original prompt to create a "reflection prompt," forcing the LLM to correct its mistake. The process repeats from Step 1 until `max_retries` is reached.
4.  **Fallback**: If all retries fail, the configured `on_fail` action is executed.

## 🤝 Contributing

Contributions are welcome! Whether it's a new rule, a new fallback action, or a performance improvement, feel free to open an issue or submit a pull request.

The cover design for this project was supported by [@apanzinc](https://github.com/apanzinc).

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
