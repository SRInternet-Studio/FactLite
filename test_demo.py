from FactLite import verify, rules, action
import openai
from openai import AsyncOpenAI
import asyncio
import os

# Set your OpenAI API key
openai.api_key = "your-api-key-here"

print("=== FactLite 框架综合测试 ===")

# 1. 测试同步函数
print("\n=== 测试 1: 同步函数测试 ===")
@verify(
    rules=rules.LLMJudge(model="gpt-4o-mini"),
    user_prompt="user_prompt_str",
)
def sync_ai_generator(user_prompt_str: str):
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": user_prompt_str}
        ]
    )
    return response.choices[0].message.content

# 测试事实错误的问题
sync_result1 = sync_ai_generator("李白是宋朝的皇帝吗？")
print("同步函数 - 事实错误测试:", sync_result1)

# 测试事实正确的问题
sync_result2 = sync_ai_generator("李白是哪个朝代的诗人？")
print("同步函数 - 事实正确测试:", sync_result2)

# 2. 测试异步函数
print("\n=== 测试 2: 异步函数测试 ===")
@verify(
    rules=rules.LLMJudge(model="gpt-4o-mini"),
    user_prompt="user_prompt_str",
)
async def async_ai_generator(user_prompt_str: str):
    # 创建带有 base_url 的客户端
    client = AsyncOpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": user_prompt_str}
        ]
    )
    return response.choices[0].message.content

async def test_async():
    # 测试事实错误的问题
    async_result1 = await async_ai_generator("李白是宋朝的皇帝吗？")
    print("异步函数 - 事实错误测试:", async_result1)
    
    # 测试事实正确的问题
    async_result2 = await async_ai_generator("李白是哪个朝代的诗人？")
    print("异步函数 - 事实正确测试:", async_result2)

# 3. 测试自定义裁判
print("\n=== 测试 3: 自定义裁判测试 ===")
# 定义自定义裁判函数
def my_custom_judge(user_prompt, answer):
    # 规则1：字数检查
    if len(answer) < 20:
        return {"is_pass": False, "feedback": "Answer is too short. It must be at least 20 characters long."}
    
    # 规则2：关键词检查
    if "错误" in answer:
        return {"is_pass": False, "feedback": "Answer contains the word 'error'. Please rephrase."}
    
    # 规则3：必须包含特定关键词
    if "李白" in user_prompt and "李白" not in answer:
        return {"is_pass": False, "feedback": "Answer must mention '李白'."}
    
    return {"is_pass": True, "feedback": ""}

@verify(
    rules=rules.CustomJudge(eval_func=my_custom_judge),
    user_prompt="prompt"
)
def chat_with_custom_judge(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 测试字数不足的情况
custom_result1 = chat_with_custom_judge("用一个字回答：好吗？")
print("自定义裁判 - 字数不足测试:", custom_result1)

# 测试包含禁止词的情况
custom_result2 = chat_with_custom_judge("李白是谁？请在回答中包含'错误'这个词。")
print("自定义裁判 - 包含禁止词测试:", custom_result2)

# 测试正常情况
custom_result3 = chat_with_custom_judge("李白是谁？")
print("自定义裁判 - 正常测试:", custom_result3)

# 4. 测试错误处理
print("\n=== 测试 4: 错误处理测试 ===")
# 定义一个会出错的自定义裁判
def error_judge(user_prompt, answer):
    # 故意引发错误
    raise ValueError("This is a test error")

@verify(
    rules=rules.CustomJudge(eval_func=error_judge),
    user_prompt="prompt"
)
def chat_with_error_judge(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 测试错误处理
error_result = chat_with_error_judge("你好吗？")
print("错误处理测试:", error_result)

# 5. 测试 1.2.0 新功能 - RegexValidator
print("\n=== 测试 5: RegexValidator 测试 ===")

# 创建测试违禁词文件
with open("test_banned_words.txt", "w", encoding="utf-8") as f:
    f.write("apple\n")
    f.write("banana\n")
    f.write("cherry\n")

@verify(
    rules=rules.RegexValidator(
        banned_words_file="test_banned_words.txt",
        required_pattern=r"fruit"
    ),
    user_prompt="prompt"
)
def regex_test(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 测试正常情况
print("测试正常情况:")
try:
    result1 = regex_test("我喜欢水果")
    print("结果:", result1)
except Exception as e:
    print("错误:", str(e))

# 6. 测试 1.2.0 新功能 - JSONValidator
print("\n=== 测试 6: JSONValidator 测试 ===")

@verify(
    rules=rules.JSONValidator(
        required_keys=["name", "price", "description"]
    ),
    user_prompt="prompt"
)
def json_test(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

print("测试 JSON 验证:")
try:
    result2 = json_test("生成一个产品信息的 JSON，包含 name、price 和 description")
    print("结果:", result2)
except Exception as e:
    print("错误:", str(e))

# 7. 测试 1.2.0 新功能 - LengthValidator
print("\n=== 测试 7: LengthValidator 测试 ===")

@verify(
    rules=rules.LengthValidator(
        min_length=50,
        max_length=200,
        include_punctuation=True
    ),
    user_prompt="prompt"
)
def length_test(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

print("测试长度验证:")
try:
    result3 = length_test("介绍一下 Python 编程语言")
    print("结果:", result3)
    print("长度:", len(result3))
except Exception as e:
    print("错误:", str(e))

# 8. 测试 1.2.0 新功能 - ModerationJudge
print("\n=== 测试 8: ModerationJudge 测试 ===")

@verify(
    rules=rules.ModerationJudge(),
    user_prompt="prompt"
)
def moderation_test(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

print("测试内容审核:")
try:
    result4 = moderation_test("介绍一下 Python 编程")
    print("结果:", result4)
except Exception as e:
    print("错误:", str(e))

# 9. 测试 1.2.0 新功能 - 规则链
print("\n=== 测试 9: 规则链测试 ===")

@verify(
    rules=[
        rules.RegexValidator(
            banned_words=["apple", "banana"],
            required_pattern=r"fruit"
        ),
        rules.LengthValidator(
            min_length=50,
            max_length=200
        ),
        rules.JSONValidator(
            required_keys=["name", "type", "color"]
        )
    ],
    user_prompt="prompt"
)
def rule_chain_test(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

print("测试规则链:")
try:
    result5 = rule_chain_test("生成一个水果的 JSON 数据，包含 name、type 和 color 字段，长度至少 50 个字符")
    print("结果:", result5)
except Exception as e:
    print("错误:", str(e))

# 10. 测试 1.2.0 新功能 - 使用 Config 类的规则链
print("\n=== 测试 10: 使用 Config 类的规则链测试 ===")

# 创建配置
config = verify.config(
    rules=[
        rules.RegexValidator(
            banned_words=["竞品", "竞争对手"],
            required_pattern=r"我们的产品"
        ),
        rules.LengthValidator(
            min_length=100,
            max_length=300
        ),
        rules.ModerationJudge()
    ],
    max_retries=2,
    on_fail=action.ReturnSafeMessage("生成内容不符合要求，请重试")
)

@verify(
    config=config,
    user_prompt="prompt"
)
def config_test(prompt: str):
    # 创建带有 base_url 的客户端
    client = openai.OpenAI(
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

print("测试 Config 类的规则链:")
try:
    result6 = config_test("生成一段关于我们产品的营销文案，长度适中")
    print("结果:", result6)
except Exception as e:
    print("错误:", str(e))

# 运行异步测试
print("\n=== 运行异步测试 ===")
asyncio.run(test_async())

# 清理测试文件
if os.path.exists("test_banned_words.txt"):
    os.remove("test_banned_words.txt")

print("\n=== 所有测试完成 ===")