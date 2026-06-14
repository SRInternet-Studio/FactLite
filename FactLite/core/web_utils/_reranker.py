"""
Semantic reranker using Sentence Transformers for FactLite framework.

This module provides a local reranker that uses sentence embeddings to 
re-rank search results based on semantic similarity to the user query.
"""

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None

from ..logging_config import logger


class LocalReranker:
    """
    A local reranker that uses sentence embeddings to re-rank search results based on relevance.
    
    This class leverages pre-trained sentence transformer models to compute semantic similarity
    between the user query and search results, returning the most relevant results.
    """
    
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        """
        Initialize the LocalReranker with a specified sentence transformer model.
        
        Args:
            model_name: The name or path of the pre-trained sentence transformer model.
                       Defaults to "BAAI/bge-small-zh-v1.5", a lightweight multilingual model
                       optimized for Chinese text similarity tasks.
        
        Raises:
            ImportError: If sentence_transformers package is not installed.
        """
        if SentenceTransformer is None:
            raise ImportError("Please install the required dependency: pip install sentence-transformers")
        
        logger.info(f"Loading sentence transformer model: {model_name} (first run may require download)...")
        self.model = SentenceTransformer(model_name)

    def rerank(self, user_query: str, search_results: list, top_k: int = 3, score_threshold: float = 0.4) -> list:
        """
        Re-rank search results based on semantic similarity to the user query.
        
        Uses cosine similarity between sentence embeddings to determine relevance,
        filtering out results below a specified confidence threshold.
        
        Args:
            user_query: The original user question or query string.
            search_results: List of search result dictionaries from DDGS, each containing
                          "title", "body", and "href" keys.
            top_k: Maximum number of top results to return. Defaults to 3.
            score_threshold: Minimum similarity score required for a result to be included.
                           Results with scores below this threshold are filtered out.
                           Defaults to 0.4.
        
        Returns:
            List of reranked results, each as a dictionary with:
            - "score": Normalized similarity score (0-1)
            - "content": The body text of the result
            - "url": The URL of the source
        """
        # Handle empty search results
        if not search_results:
            logger.warning("No search results provided for reranking")
            return []

        # Extract document bodies from search results
        documents = [res.get("body", "") for res in search_results]

        # Generate embeddings for query and documents
        # Convert to tensor for efficient computation
        query_embedding = self.model.encode(user_query, convert_to_tensor=True)
        doc_embeddings = self.model.encode(documents, convert_to_tensor=True)

        # Compute cosine similarity between query and document embeddings
        # cos_sim returns a 2D tensor, we extract the first row
        cosine_scores = util.cos_sim(query_embedding, doc_embeddings)[0]

        # Pair scores with their corresponding documents and original results
        # Then sort by similarity score in descending order
        scored_results = zip(cosine_scores.tolist(), documents, search_results)
        scored_results = sorted(scored_results, key=lambda x: x[0], reverse=True)

        # Filter results based on threshold and select top_k
        best_results = []
        for score, doc, original_res in scored_results[:top_k]:
            if score > score_threshold: 
                best_results.append({
                    "score": round(score, 3),
                    "content": doc,
                    "url": original_res.get("href", "")
                })
                logger.debug(f"Added result with score {round(score, 3)}: {doc[:50]}...")

        logger.info(f"Reranking completed: {len(best_results)}/{len(search_results)} results passed threshold")
        return best_results