"""
Pre-retrieval augmenter for FactLite framework.

This module provides an intelligent retrieval augmenter that:
1. Analyzes user input to determine if web search is needed
2. Performs web search if necessary
3. Applies semantic reranking
4. Returns augmented prompt with search results

The augmenter can operate in two modes:
- Auto-route: Automatically determine if search is needed based on query analysis
- Always search: Always perform web search regardless of query type
"""

import traceback
from typing import Optional, Dict
import asyncio
from ..logging_config import logger
from ._search_utils import (
    extract_keywords, 
    generate_search_query, 
    web_search, 
    llm_needs_search,
    async_llm_needs_search
)

try:
    from ._reranker import LocalReranker
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logger.warning("sentence-transformers not installed, reranking disabled")


class Augmenter:
    """
    Intelligent pre-retrieval augmenter for enhancing prompts with web search results.
    
    This class provides automatic intent detection and web search capabilities
    to augment user prompts with relevant information before sending to LLM.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_results: int = 15,
        top_k: int = 3,
        backend: str = "auto",
        proxy: Optional[str] = None,
        reranker_model: str = "BAAI/bge-small-zh-v1.5",
        use_reranker: bool = True,
        auto_route: bool = True,
        score_threshold: float = 0.4
    ):
        """
        Initialize the Augmenter with specified configuration.
        
        Args:
            model: LLM model name (currently used for compatibility)
            api_key: API key for LLM (currently used for compatibility)
            base_url: Base URL for LLM API (currently used for compatibility)
            max_results: Maximum number of search results to fetch
            top_k: Number of top reranked results to include in context
            backend: Search backend ("brave", "duckduckgo", "google", "grokipedia", "mojeek", "startpage", "wikipedia", "yandex", default="auto")
            proxy: Proxy server URL
            reranker_model: Sentence transformer model name for reranking
            use_reranker: Whether to use semantic reranking
            auto_route: Whether to automatically determine if search is needed
            score_threshold: Minimum similarity score for reranked results
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_results = max_results
        self.top_k = top_k
        self.backend = backend
        self.proxy = proxy
        self.use_reranker = use_reranker and RERANKER_AVAILABLE
        self.auto_route = auto_route
        self.score_threshold = score_threshold
        self.reranker_model = reranker_model
        self.reranker = None
        
        # Initialize reranker if enabled
        if self.use_reranker:
            try:
                self.reranker = LocalReranker(model_name=reranker_model)
                logger.info(f"Reranker initialized with model: {reranker_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize reranker: {e}. Disabling reranking.")
                self.use_reranker = False
    
    async def _needs_search_impl(self, user_prompt: str, is_async: bool) -> bool:
        """
        Internal implementation of intent detection.
        
        Args:
            user_prompt: The user's input text
            is_async: Whether to execute asynchronously
            
        Returns:
            True if search is recommended, False otherwise
        """
        if not self.auto_route:
            return True
        
        if is_async:
            needs_search = await async_llm_needs_search(
                user_query=user_prompt,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.debug(f"Async LLM intent classification result: {'needs search' if needs_search else 'no search needed'}")
        else:
            needs_search = llm_needs_search(
                user_query=user_prompt,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.debug(f"LLM intent classification result: {'needs search' if needs_search else 'no search needed'}")
        
        return needs_search
    
    async def _execute_search_impl(self, search_query: str, is_async: bool) -> list:
        """
        Internal implementation of web search.
        
        Args:
            search_query: The search query string
            is_async: Whether to execute asynchronously
            
        Returns:
            List of search results
        """
        try:
            logger.info(f"Performing {'async ' if is_async else ''}search with query: {search_query}")
            
            if is_async:
                search_results = await asyncio.to_thread(
                    web_search,
                    query=search_query,
                    backend=self.backend,
                    max_results=self.max_results,
                    proxy=self.proxy
                )
            else:
                search_results = web_search(
                    query=search_query,
                    backend=self.backend,
                    max_results=self.max_results,
                    proxy=self.proxy
                )
            
            logger.info(f"{'Async ' if is_async else ''}Search completed: {len(search_results)} results found")
            return search_results
        except Exception as e:
            logger.error(f"{'Async ' if is_async else ''}Search failed: {e}")
            return []
    
    async def _execute_rerank_impl(self, user_prompt: str, search_results: list, is_async: bool) -> list:
        """
        Internal implementation of reranking.
        
        Args:
            user_prompt: The user's input text
            search_results: List of search results to rerank
            is_async: Whether to execute asynchronously
            
        Returns:
            List of reranked results
        """
        if not self.use_reranker or not self.reranker:
            return [{"content": res.get("body", ""), "url": res.get("href", "")} 
                    for res in search_results[:self.top_k]]
        
        if is_async:
            reranked_results = await asyncio.to_thread(
                self.reranker.rerank,
                user_query=user_prompt,
                search_results=search_results,
                top_k=self.top_k,
                score_threshold=self.score_threshold
            )
        else:
            reranked_results = self.reranker.rerank(
                user_query=user_prompt,
                search_results=search_results,
                top_k=self.top_k,
                score_threshold=self.score_threshold
            )
        
        logger.info(f"{'Async ' if is_async else ''}Reranking completed: {len(reranked_results)}/{len(search_results)} results passed threshold")
        return reranked_results
    
    def _build_augmented_prompt(self, user_prompt: str, reranked_results: list) -> str:
        """
        Build the augmented prompt from reranked results.
        
        Args:
            user_prompt: The original user input
            reranked_results: List of reranked search results
            
        Returns:
            The augmented prompt string
        """
        if not reranked_results:
            return user_prompt
        
        context = "\n".join([
            f"[{i+1}] {result['content'][:500]}..." 
            for i, result in enumerate(reranked_results)
        ])
        
        return f"""Based on the following reference information, please answer the user's question:

[Reference Information]
{context}

[User Question]
{user_prompt}

Please provide a comprehensive and accurate answer based on the reference information above.
"""
    
    async def _augment_impl(self, user_prompt: str, is_async: bool) -> Dict:
        """
        Unified implementation of augment logic.
        
        Args:
            user_prompt: The original user input
            is_async: Whether to execute asynchronously
            
        Returns:
            Dictionary containing augmented prompt and metadata
        """
        # Analyze query - intent detection
        needs_search = await self._needs_search_impl(user_prompt, is_async)
        keywords = extract_keywords(user_prompt)
        search_query = generate_search_query(user_prompt)
        
        analysis = {
            "needs_search": needs_search,
            "keywords": keywords,
            "search_query": search_query,
            "prompt_length": len(user_prompt)
        }
        
        logger.info(f"{'Async ' if is_async else ''}Query analysis: needs_search={needs_search}, keywords={keywords}")
        
        # Perform search if needed
        search_results = []
        search_performed = False
        if needs_search:
            search_results = await self._execute_search_impl(search_query, is_async)
            search_performed = True
        
        # Apply reranking
        reranked_results = await self._execute_rerank_impl(user_prompt, search_results, is_async)
        
        # Build augmented prompt
        augmented_prompt = self._build_augmented_prompt(user_prompt, reranked_results)
        
        return {
            "augmented_prompt": augmented_prompt,
            "original_prompt": user_prompt,
            "search_performed": search_performed,
            "search_results": reranked_results,
            "analysis": analysis
        }
    
    def augment(self, user_prompt: str) -> Dict:
        """
        Augment user prompt with web search results if needed (sync version).
        
        This is the main entry point that:
        1. Analyzes the user's intent
        2. Performs web search if needed
        3. Applies semantic reranking
        4. Returns augmented prompt and metadata
        
        Args:
            user_prompt: The original user input
            
        Returns:
            Dictionary containing:
            - "augmented_prompt": The enhanced prompt with search results
            - "original_prompt": The original user prompt
            - "search_performed": Boolean indicating if search was performed
            - "search_results": List of search results used
            - "analysis": Query analysis metadata
        """
        coro = self._augment_impl(user_prompt, is_async=False)
    
        try:
            # 尝试获取当前的事件循环
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result()
        except Exception as e:
            logger.error(f"Event loop conflict in sync mode: {traceback.format_exc()}. Falling back to original prompt.")
            return {
                "augmented_prompt": user_prompt,
                "original_prompt": user_prompt,
                "search_performed": False,
                "search_results": [],
                "analysis": {}
            }
    
    async def augment_async(self, user_prompt: str) -> Dict:
        """
        Augment user prompt with web search results if needed (async version).
        
        Uses asyncio.to_thread for blocking operations and AsyncOpenAI
        for non-blocking API calls.
        
        Args:
            user_prompt: The original user input
            
        Returns:
            Dictionary containing:
            - "augmented_prompt": The enhanced prompt with search results
            - "original_prompt": The original user prompt
            - "search_performed": Boolean indicating if search was performed
            - "search_results": List of search results used
            - "analysis": Query analysis metadata
        """
        return await self._augment_impl(user_prompt, is_async=True)