# FactLite 🪶

[English](README.md) | 中文

**只需一个装饰器，为你的大语言模型（LLM）装上“System 2”大脑。**

[![PyPI 版本](https://badge.fury.io/py/FactLite.svg)](https://badge.fury.io/py/FactLite)
[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-310/)

---

在部署生成式 AI 的“最后一公里”，**模型幻觉总是最终的大 Boss**。像 LangChain 这样的大型框架会引入过多的模板代码和复杂性，而直接调用原始 API 又没有任何安全保障。

**FactLite** 是一个为生产环境而生的、超轻量级的 Python 微框架，专为解决这一痛点而设计。它从顶级的 **“智能体（Agentic）Reflexion”架构** 中汲取灵感，通过一个自动化的、自我修正的评估循环来增强你现有的 LLM 调用，而无需你重构代码库。

## 🚀 核心特性

*   **✨ 零侵入式设计:** 只需一个 `@verify` 装饰器，就能为任何函数添加事实核查与自我修正能力。完全无需重写你现有的业务逻辑。
*   **⚡️ 原生异步 & 并发安全:** 从底层设计上就支持 `async/await`。评估过程在一个独立的线程中运行，以防止阻塞你的主事件循环，这使其完美适用于像 FastAPI 这样的高性能 Web 后端。
*   **🤖 智能体工作流:** 实现了一个自动化的 **生成 -> 评估 -> 反思** 循环。你的 LLM 会被迫审视并迭代改进它自己的答案，直到满足你设定的质量标准。
*   **🧩 可扩展 & 插件化:**
    *   **自带“裁判”**: 你可以使用内置的 `LLMJudge`，也可以通过 `CustomJudge` 创建自己的验证逻辑（例如：正则表达式、数据库查询、类型检查）。
    *   **自定义失败策略**: 通过自定义 `FallbackAction`，你可以精确定义失败后的行为——是抛出异常，返回一条安全无害的消息，还是触发一个 webhook。
*   **🌐 框架无关:** FactLite 不关心你如何调用 LLM。无论你用的是 `openai` 的 SDK、`anthropic` 的客户端，还是一个简单的 `requests.post` 去调用本地模型，只要它是一个返回字符串的 Python 函数，FactLite 就能为它保驾护航。

## 📦 安装

```bash
pip install FactLite
```

## 🎯 快速上手：感受“灵光一现”的瞬间

看看将你的代码从一个普通的 API 调用升级为一个能自我修正的智能体有多么简单。

**之前：一个标准的、毫无保护的 LLM 调用。**

```python
import openai

client = openai.OpenAI(api_key="你的密钥")

def ask_ai(question: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

# 这可能会返回一个事实错误的答案，而你永远不会知道。
print(ask_ai("李白是宋朝的皇帝吗？"))
```

**之后：只需一行代码，即可受到 FactLite 的保护。**

```python
import openai
from FactLite import verify, rules, action

client = openai.OpenAI(api_key="你的密钥")

# 配置一个强大的“裁判”和你的 API 密钥
config = verify.config(
    rule=rules.LLMJudge(model="gpt-4o-mini", api_key="你的密钥"), # 使用 gpt-4o-mini 作为“裁判”
    max_retries=1 # 最多重试 1 次
)

@verify(config=config, user_prompt="question") # 加上这个装饰器
def ask_ai(question: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

# 现在，函数会在返回结果前自动修正答案。
print(ask_ai("李白是宋朝的皇帝吗？"))
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

### 异步支持

FactLite 会自动检测并支持 `async` 异步函数。

```python
from openai import AsyncOpenAI

async_client = AsyncOpenAI(api_key="你的密钥")

@verify(config=config, user_prompt="question")
async def ask_ai_async(question: str):
    response = await async_client.chat.completions.create(...)
    return response.choices[0].message.content

# 运行它
import asyncio
asyncio.run(ask_ai_async("给我讲讲唐朝的历史。"))
```

### 自定义规则 (`CustomJudge`)

除了基于 LLM 的检查，你还可以强制执行任何你能想到的本地业务逻辑。

```python
def company_policy_judge(prompt, answer):
    # 规则1：不允许过短的回答
    if len(answer) < 50:
        return {"is_pass": False, "feedback": "回答太短了，请再详细一点。"}
    # 规则2：不能提及竞争对手
    if "谷歌" in answer:
        return {"is_pass": False, "feedback": "请不要提及竞争对手的名字。"}
    return {"is_pass": True, "feedback": ""}

@verify(rule=rules.CustomJudge(eval_func=company_policy_judge), user_prompt="prompt")
def ask_support_bot(prompt: str):
    # ... 你的 LLM 调用逻辑
    pass
```

### 联网增强验证 (`Web_LLMJudge`)

利用网络搜索来验证答案是否符合最新信息，非常适合时效性强或快速变化的话题。

```python
@verify(
    rule=rules.Web_LLMJudge(
        model="gpt-4o-mini",
        max_results=3,  # 使用的搜索结果数量
        backend="duckduckgo"  # 搜索后端
    ),
    user_prompt="question"
)
def ask_ai_about_current_events(question: str):
    # ... 你的 LLM 调用逻辑
    pass
```

**Web_LLMJudge 参数说明：**
- `model`：用于评估的 OpenAI 模型
- `max_results`：使用的搜索结果数量（默认：3）
- `backend`：搜索后端，支持 "duckduckgo"、"bing"、"google"（默认："duckduckgo"）
- `proxy`：可选的搜索代理
- `api_key`：可选的 OpenAI API 密钥（默认为全局 `openai.api_key`）
- `base_url`：可选的 OpenAI API 基础 URL

### 自定义失败兜底操作 (`FallbackAction`)

当一个答案在所有重试后仍然失败时，精确定义接下来会发生什么。

```python
from FactLite import action

@verify(
    ...,
    on_fail=action.ReturnSafeMessage("很抱歉，我现在无法对该问题提供一个确切的答案。")
)
def ask_sensitive_question(...):
    pass

@verify(..., on_fail=action.RaiseError())
def ask_critical_question(...):
    pass
```

## 🛠️ 工作原理

FactLite 的 `@verify` 装饰器将你的函数包装在一个简单而强大的控制循环中：

1.  **生成 (Generate)**: 调用你的原始函数以生成一个初步的答案草稿。
2.  **评估 (Evaluate)**: 调用配置好的 `rule` (例如 `LLMJudge`) 来评估草稿的质量。
3.  **反思与重试 (Reflect & Retry)**:
    *   如果评估通过，答案将直接返回给用户。
    *   如果评估失败，反馈意见会与原始提示词结合，形成一个“反思提示词”，迫使 LLM 纠正自己的错误。然后从第 1 步重新开始，直到达到 `max_retries` 上限。
4.  **兜底 (Fallback)**: 如果所有重试都失败了，将执行配置好的 `on_fail` 兜底操作。

## 🤝 贡献

欢迎参与贡献！无论是提交一个新的规则、一个新的兜底操作，还是一个性能改进，都欢迎你提出 Issue 或提交 Pull Request。

## 📄 许可证

本项目基于 MIT 许可证。详情请参阅 `LICENSE` 文件。