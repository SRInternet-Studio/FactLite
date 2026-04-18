## 一、 `CustomJudge` 的开发规范（Design Specification）

### 1. 输入规范 (Input Contract)
用户传入的自定义裁判函数（`eval_func`）必须接受两个**位置/关键字参数**：
*   `user_prompt` (str): 用户的原始提问。
*   `answer` (str): 大模型生成的初步回答。

### 2. 输出规范 (Output Contract)
这是最重要的一点！为了让框架底层的 `verify.py` 能够统一处理，自定义函数**必须且只能返回一个包含特定 Key 的字典（Dict）**：

```python
{
    "is_pass": True/False,  # 布尔值，代表是否通过了质检
    "feedback": "...",      # 字符串，如果不通过，说明具体原因；如果通过，可为空
    "no_retry": True/False  # 可选布尔值，若为True，框架将直接执行兜底策略，不再重试
}
```

**说明**：
- `is_pass` (必需): 布尔值，表示是否通过质检
- `feedback` (必需): 字符串，失败时的具体原因，成功时可为空字符串
- `no_retry` (可选): 布尔值，默认为 False。当设置为 True 时，框架会直接执行兜底策略，不再进行重试。适用于那些不是由 AI 生成内容本身导致的错误，如配置错误、外部服务故障等。

## 二、 示例

### 示例 1：基本使用

比如，我们写一个**“绝对不能包含脏话，且字数不能少于10个字”**的本地正则校验器（完全不需要调 API）：

```python
# test_custom.py
from FactLite import verify, rules
import openai

# 1. 开发者自己定义一个普通的 Python 函数
def my_strict_company_policy_judge(prompt, answer):
    # 规则1：字数太少不行
    if len(answer) < 10:
        return {"is_pass": False, "feedback": "Your answer is too short. It must be at least 10 characters long."}
    
    # 规则2：不能包含竞品的名字
    banned_words = ["Apple", "iPhone"]
    for word in banned_words:
        if word.lower() in answer.lower():
            return {"is_pass": False, "feedback": f"You are forbidden from mentioning the competitor '{word}'. Change the wording."}
    
    # 如果都没问题，放行
    return {"is_pass": True, "feedback": ""}


# 2. 像搭积木一样塞进你的框架
@verify(
    rules=rules.CustomJudge(eval_func=my_strict_company_policy_judge),
    user_prompt="prompt"
)
def chat(prompt: str):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 试着让他犯错
print(chat(prompt="用一句话夸一下我们的手机，可以提到iPhone作为对比。"))
```

### 示例 2：使用 no_retry 标记

当验证失败是由非 AI 生成内容导致的错误时，使用 `no_retry=True` 可以避免不必要的重试：

```python
# test_custom_no_retry.py
from FactLite import verify, rules
import openai
import requests

# 自定义裁判函数，检查回答是否包含有效链接
def link_validator(prompt, answer):
    # 提取回答中的链接
    import re
    links = re.findall(r'https?://\S+', answer)
    
    # 检查链接是否可访问
    for link in links:
        try:
            response = requests.get(link, timeout=5)
            if response.status_code >= 400:
                return {"is_pass": False, "feedback": f"Link {link} is not accessible."}
        except Exception as e:
            # 网络错误，不需要重试
            return {"is_pass": False, "feedback": f"Error checking link: {str(e)}", "no_retry": True}
    
    return {"is_pass": True, "feedback": ""}

@verify(
    rules=rules.CustomJudge(eval_func=link_validator),
    user_prompt="prompt"
)
def generate_with_links(prompt: str):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 测试
print(generate_with_links(prompt="推荐一些学习Python的网站，包含具体链接。"))
```

## 三、 最佳实践

1. **错误处理**：在自定义函数中添加适当的错误处理，确保函数不会因为异常而崩溃。

2. **性能考虑**：如果自定义函数需要进行耗时操作（如网络请求），请考虑其对整体性能的影响。

3. **清晰的反馈**：提供详细、具体的反馈信息，这样 AI 在重生成时可以更好地纠正错误。

4. **合理使用 no_retry**：对于那些不是由 AI 生成内容导致的错误（如配置错误、外部服务故障），使用 `no_retry=True` 可以提高效率。

5. **模块化设计**：将复杂的验证逻辑拆分为多个小函数，提高代码可读性和可维护性。