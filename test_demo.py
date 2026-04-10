from FactLite import verify, rules, action
import openai
from openai import AsyncOpenAI
import asyncio

# Set your OpenAI API key
openai.api_key = "your_api_key"

# 配置
config = verify.config(
    rule=rules.LLMJudge(model="gpt-4o-mini", 
                        base_url="https://free.v36.cm/v1", 
                        api_key="your_api_key"),
    max_retries=2,
    on_fail=action.ReturnBest
)

# 1. 测试同步函数
print("=== 测试 1: 同步函数测试 ===")
@verify(
    config=config,
    user_prompt="user_prompt_str",
)
def sync_ai_generator(user_prompt_str: str):
    # 创建带有 base_url 的客户端
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
    config=config,
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
    rule=rules.CustomJudge(eval_func=my_custom_judge),
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
    rule=rules.CustomJudge(eval_func=error_judge),
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

# 运行异步测试
print("\n=== 运行异步测试 ===")
asyncio.run(test_async())

print("\n=== 所有测试完成 ===")