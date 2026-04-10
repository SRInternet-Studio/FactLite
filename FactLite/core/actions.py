from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class FallbackAction(ABC):
    """Base class for all fallback actions."""
    @abstractmethod
    def execute(self, prompt: str, last_answer: str, feedback: str) -> str:
        """Execute the fallback action.
        
        Args:
            prompt (str): The original user question
            last_answer (str): The model's last generated answer
            feedback (str): The feedback from the judge
            
        Returns:
            str: The fallback action's response
        """
        pass

class ReturnBest(FallbackAction):
    """Return the last generated answer despite failing verification."""
    def execute(self, prompt: str, last_answer: str, feedback: str) -> str:
        logger.warning("Returning the last generated answer despite failing verification.")
        return last_answer

class RaiseError(FallbackAction):
    """Raise an exception if the answer fails verification."""
    def execute(self, prompt: str, last_answer: str, feedback: str) -> str:
        logger.error("Raising exception due to factual verification failure.")
        raise Exception(f"Answer failed factual verification. Last feedback: {feedback}")

class ReturnSafeMessage(FallbackAction):
    """Return a safe message if the answer fails verification."""
    def __init__(self, safe_message="抱歉，AI 暂时无法针对该问题给出有确切把握的回答。"):
        self.safe_message = safe_message
        
    def execute(self, prompt: str, last_answer: str, feedback: str) -> str:
        logger.warning(f"Returning safe message. Original hallucination feedback: {feedback}")
        return self.safe_message