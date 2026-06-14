import inspect
import logging
import asyncio

logger = logging.getLogger(__name__)

class RuleChain:
    """RuleChain class for executing a chain of rules sequentially
    
    This class allows users to directly call RuleChain.evaluate(prompt, answer)
    to get validation feedback without using the decorator, giving them more control
    over the state flow in their own Agent frameworks.
    """
    
    def __init__(self, rules):
        """Initialize RuleChain with rules
        
        Args:
            rules: A single BaseRule or list of BaseRule objects
        """
        self.rules = rules
    
    async def evaluate_async(self, prompt, answer):
        """Execute rules asynchronously
        
        Args:
            prompt: The original user prompt
            answer: The model's answer
            
        Returns:
            tuple: (is_pass, feedback, no_retry)
        """
        # Convert single rule to list
        rule_list = self.rules if isinstance(self.rules, list) else [self.rules]
        
        for i, rule in enumerate(rule_list):
            logger.info(f"Executing rule {i+1}/{len(rule_list)}...")
            if inspect.iscoroutinefunction(rule.evaluate):
                evaluation_result = await rule.evaluate(prompt, answer)
            else:
                evaluation_result = await asyncio.to_thread(rule.evaluate, prompt, answer)
            
            is_pass = evaluation_result.get("is_pass", False)
            feedback = evaluation_result.get("feedback", "")
            no_retry = evaluation_result.get("no_retry", False)
            
            if not is_pass:
                logger.error(f"❌ Rule {i+1} failed: {feedback}")
                return (is_pass, feedback, no_retry)
        
        return (True, "", False)
    
    def evaluate(self, prompt, answer):
        """Execute rules synchronously
        
        Args:
            prompt: The original user prompt
            answer: The model's answer
            
        Returns:
            tuple: (is_pass, feedback, no_retry)
        """
        # Convert single rule to list
        rule_list = self.rules if isinstance(self.rules, list) else [self.rules]
        
        for i, rule in enumerate(rule_list):
            logger.info(f"Executing rule {i+1}/{len(rule_list)}...")
            evaluation_result = rule.evaluate(prompt, answer)
            
            is_pass = evaluation_result.get("is_pass", False)
            feedback = evaluation_result.get("feedback", "")
            no_retry = evaluation_result.get("no_retry", False)
            
            if not is_pass:
                logger.error(f"❌ Rule {i+1} failed: {feedback}")
                return (is_pass, feedback, no_retry)
        
        return (True, "", False)