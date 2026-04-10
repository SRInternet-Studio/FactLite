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
    "feedback": "..."       # 字符串，如果不通过，说明具体原因；如果通过，可为空
}
```

## 二、 示例

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
    rule=rules.CustomJudge(eval_func=my_strict_company_policy_judge),
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