"""
Web search utilities for FactLite framework.

This module provides core web search functionality including:
- Keyword extraction with jieba support
- Search query generation
- Web search execution using DDGS
- LLM-based intent detection for determining if web search is needed
"""

import re
import json
from collections import Counter
from ddgs import DDGS
import ddgs.exceptions as ddgs_exceptions

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Intent classification prompt
INTENT_ROUTER_PROMPT = """
You are a router that determines user intent. 
Please determine whether the following user queries require the latest real-time information or objective external encyclopedia knowledge to answer. 
If the query is about daily greetings, writing code, writing poetry, translation and other purely logical generation tasks, return FALSE. 
If it's about checking news, looking up data, asking about specific people or events, etc., return TRUE. 
You are only allowed to output TRUE or FALSE.

User query: """.strip()

# Combined stop words for English and Chinese
STOP_WORDS = set([
    # English stop words
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", 
    "for", "of", "with", "by", "from", "as", "is", "are", "was", 
    "were", "be", "been", "being", "have", "has", "had", "do", 
    "does", "did", "will", "would", "could", "should", "may", "might",
    "this", "that", "these", "those", "it", "its", "they", "their",
    "what", "which", "who", "whom", "whose", "my", "your", "his", "her",
    "we", "us", "you", "he", "she", "him", "me", "i",
    # Chinese stop words
    "的", "了", "和", "是", "就", "都", "而", "及", "与", "着", "或",
    "一个", "没有", "我们", "你们", "他们", "它们", "这个", "那个",
    "什么", "怎么", "如何", "为什么", "因为", "所以", "但是", "然而",
    "在", "有", "不", "也", "很", "还", "要", "会", "可以", "能",
    "应该", "必须", "可能", "需要", "已经", "正在", "曾经", "将要",
    "这", "那", "此", "其", "某", "每", "各", "所有", "任何", "一些",
    "其他", "另外", "以及", "等等", "例如", "比如", "包括", "通过"
])


def extract_keywords(text: str) -> list:
    """
    Extract keywords from text using jieba (if available) or regex fallback.
    
    Supports both Chinese and English text by leveraging jieba's powerful
    Chinese word segmentation capabilities.
    
    Args:
        text: The text to extract keywords from
        
    Returns:
        List of extracted keywords (top 5 most frequent non-stop words)
    """
    # Use jieba for better Chinese tokenization if available
    if JIEBA_AVAILABLE:
        words = [word.lower() for word in jieba.cut(text)]
    else:
        # Fallback to regex-based tokenization
        words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter out stop words and short words
    keywords = [word for word in words if word not in STOP_WORDS and len(word) > 1]
    
    # Return top 5 most frequent keywords
    keyword_counts = Counter(keywords)
    top_keywords = [keyword for keyword, _ in keyword_counts.most_common(5)]
    
    return top_keywords


def generate_search_query(user_prompt: str) -> str:
    """
    Generate optimized search query from user prompt by extracting keywords.
    
    Args:
        user_prompt: The original user prompt
        
    Returns:
        The generated search query string
    """
    keywords = extract_keywords(user_prompt)
    query = " ".join(keywords)
    # Fallback to original prompt if no keywords extracted
    return query if query else user_prompt


def web_search(query: str, backend: str = "auto", max_results: int = 15, proxy: str = None) -> list:
    """
    Perform web search using DDGS.
    
    Args:
        query: Search query string
        backend: Search backend ("brave", "duckduckgo", "google", "grokipedia", "mojeek", "startpage", "wikipedia", "yandex", default="auto")
        max_results: Maximum number of results to return
        proxy: Proxy server URL
        
    Returns:
        List of search result dictionaries with "title", "body", and "href" keys
        
    Raises:
        ddgs_exceptions.DDGSException: If search fails
    """
    try:
        with DDGS(proxy=proxy) if proxy else DDGS() as ddgs:
            results = list(ddgs.text(query=query, backend=backend, max_results=max_results))
        return results
    except ddgs_exceptions.DDGSException as e:
        raise e


def llm_needs_search(
    user_query: str,
    model: str = "gpt-4o-mini",
    api_key: str = None,
    base_url: str = None
) -> bool:
    """
    Use LLM to determine if a user query requires web search.
    
    This function uses a small LLM to classify user intent and determine
    whether the query requires real-time information or external knowledge.
    
    Args:
        user_query: The user's input query
        model: LLM model name to use for intent classification
        api_key: OpenAI API key (defaults to global openai.api_key)
        base_url: OpenAI API base URL
        
    Returns:
        True if web search is needed, False otherwise.
        Falls back to pattern-based detection if LLM is unavailable.
    """
    if not OPENAI_AVAILABLE:
        return pattern_based_needs_search(user_query)
    
    try:
        api_key = api_key or getattr(openai, 'api_key', None)
        client = openai.OpenAI(api_key=api_key, base_url=base_url) if hasattr(openai, "OpenAI") else openai
        
        prompt = f"{INTENT_ROUTER_PROMPT}\n{user_query}"
        
        if hasattr(openai, "OpenAI"):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an intent classification assistant. Return only TRUE or FALSE."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0
            )
            result = response.choices[0].message.content.strip().upper()
        else:
            response = client.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an intent classification assistant. Return only TRUE or FALSE."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0
            )
            result = response.choices[0].message['content'].strip().upper()
        
        return result == "TRUE"
    except Exception:
        # Fallback to pattern-based detection on any error
        return pattern_based_needs_search(user_query)


async def async_llm_needs_search(
    user_query: str,
    model: str = "gpt-4o-mini",
    api_key: str = None,
    base_url: str = None
) -> bool:
    """
    Async version of llm_needs_search using AsyncOpenAI.
    
    This function uses asyncio.to_thread for synchronous operations
    and AsyncOpenAI for async API calls.
    
    Args:
        user_query: The user's input query
        model: LLM model name to use for intent classification
        api_key: OpenAI API key (defaults to global openai.api_key)
        base_url: OpenAI API base URL
        
    Returns:
        True if web search is needed, False otherwise.
        Falls back to pattern-based detection if LLM is unavailable.
    """
    if not OPENAI_AVAILABLE:
        return pattern_based_needs_search(user_query)
    
    try:
        api_key = api_key or getattr(openai, 'api_key', None)
        
        # Use AsyncOpenAI if available
        if hasattr(openai, "AsyncOpenAI"):
            async_client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            prompt = INTENT_ROUTER_PROMPT.format(user_query=user_query)
            
            response = await async_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an intent classification assistant. Return only TRUE or FALSE."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0
            )
            result = response.choices[0].message.content.strip().upper()
            return result == "TRUE"
        else:
            # Fallback to sync version in thread pool
            import asyncio
            return await asyncio.to_thread(
                llm_needs_search,
                user_query=user_query,
                model=model,
                api_key=api_key,
                base_url=base_url
            )
    except Exception:
        # Fallback to pattern-based detection on any error
        return pattern_based_needs_search(user_query)


def pattern_based_needs_search(user_query: str) -> bool:
    """
    Pattern-based intent detection as fallback.
    
    Uses keyword matching to determine if a query likely needs web search.
    
    Args:
        user_query: The user's input query
        
    Returns:
        True if web search is likely needed, False otherwise
    """
    # Question indicators that suggest search might be helpful
    question_indicators = [
        "是什么", "什么是", "是谁", "何时", "何时是", "多少", "几",
        "如何", "怎么样", "为什么", "原因", "结果", "影响",
        "最新", "最新消息", "最新进展", "今天", "现在",
        "谁", "哪个", "哪里", "哪儿", "哪个国家", "哪个城市",
        "how", "what", "when", "who", "where", "why", "which",
        "latest", "current", "today", "now", "recent"
    ]
    
    # Keywords that strongly suggest fact-based queries requiring search
    fact_keywords = [
        "事实", "真相", "数据", "统计", "数字", "年份", "时间",
        "事件", "历史", "新闻", "报道", "发布", "公告",
        "fact", "truth", "data", "statistics", "number", "year",
        "event", "history", "news", "report", "announcement"
    ]
    
    # Keywords that suggest creative/writing tasks (usually don't need search)
    creative_keywords = [
        "写", "创作", "生成", "编", "设计", "构思",
        "故事", "小说", "诗歌", "文章", "段落", "句子",
        "写一篇", "写一个", "创作一个", "生成一个",
        "write", "create", "generate", "compose", "design",
        "story", "poem", "article", "essay", "paragraph", "sentence"
    ]
    
    query_lower = user_query.lower()
    
    # Check for creative keywords first (these usually don't need search)
    for keyword in creative_keywords:
        if keyword in query_lower:
            return False
    
    # Check for question indicators
    for indicator in question_indicators:
        if indicator in query_lower:
            return True
    
    # Check for fact-based keywords
    for keyword in fact_keywords:
        if keyword in query_lower:
            return True
    
    # Default: assume search is helpful for most queries
    return True