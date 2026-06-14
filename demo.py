from FactLite import Augmenter, verify, rules, action
from FactLite.core.logging_config import logger
import openai
from openai import AsyncOpenAI

openai.api_key = "your-api-key-here"
# client = AsyncOpenAI(base_url="https://api.deepseek.com/v1", timeout=45.0)  # Async version
client = openai.OpenAI(api_key=openai.api_key, base_url="https://api.deepseek.com/v1", timeout=45.0)

augmenter = Augmenter(
    model="deepseek-chat",
    api_key=openai.api_key,
    base_url="https://api.deepseek.com/v1",
    max_results=5,
    top_k=2,
    use_reranker=True,  # Enable reranker for faster testing
    auto_route=True,
    score_threshold=0.4,
    proxy="http://127.0.0.1:7897",
)

config = verify.config(
    rules=rules.Web_LLMJudge(
        model="deepseek-chat",
        api_key=openai.api_key,
        base_url="https://api.deepseek.com/v1",
        max_results=3,
        top_k=2,
        use_reranker=False,
        auto_route=True,
        proxy="http://127.0.0.1:7897",
    ),
    max_retries=2,
    on_fail=action.ReturnBest()
)

@verify(config=config, user_prompt="prompt")
def generate_response(prompt: str) -> str:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.5
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    # user_input = augmenter.augment_async(input="请输入你的问题：")["augmented_prompt"] # Async version
    user_input = augmenter.augment(input("请输入你的问题："))["augmented_prompt"]
    logger.info(f"Enhanced user input: {user_input}")
    logger.info(f"Model response: {generate_response(user_input)}")
