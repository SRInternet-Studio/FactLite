import functools
import inspect
import openai
import logging
import asyncio
from .actions import ReturnBest
from .config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [FactLite] - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def _get_prompt_value(user_prompt, args, kwargs):
    """Get the prompt value from either kwargs or args"""
    prompt_value = kwargs.get(user_prompt)
    arg_index = None
    if not prompt_value and args:
        prompt_value = args[0]
        arg_index = 0
    return prompt_value, arg_index

def _update_prompt(current_prompt, arg_index, args, kwargs, user_prompt):
    """Update the prompt in either args or kwargs"""
    new_args = list(args)
    new_kwargs = kwargs.copy()
    if arg_index is not None:
        new_args[arg_index] = current_prompt
    else:
        new_kwargs[user_prompt] = current_prompt
    return new_args, new_kwargs

def _generate_reflection_prompt(prompt_value, best_answer, feedback):
    """Generate reflection prompt"""
    return f"""[CRITICAL SYSTEM DIRECTIVE: SELF-CORRECTION REQUIRED]
The user asked: "{prompt_value}"

Your previous generated draft:
---
{best_answer}
---

The Automated Validator rejected your draft with the following fatal error:
🚨 **{feedback}** 🚨

**YOUR TASK**:
You must rewrite the draft to completely resolve the error above. 
- If words are banned, use clever synonyms.
- If it's too long, violently delete non-essential sentences.
- If JSON is broken, output ONLY raw valid JSON without any markdown or explanations.

Take a deep breath and provide the flawless final answer below:"""

async def _execute_rules_async(rules, prompt_value, answer):
    """Execute a list of rules sequentially asynchronously
    
    Args:
        rules: A single BaseRule or list of BaseRule objects
        prompt_value: The original user prompt
        answer: The model's answer
        
    Returns:
        tuple: (is_pass, feedback, no_retry)
    """
    # Convert single rule to list
    rule_list = rules if isinstance(rules, list) else [rules]
    
    for i, rule in enumerate(rule_list):
        logger.info(f"Executing rule {i+1}/{len(rule_list)}...")
        if inspect.iscoroutinefunction(rule.evaluate):
            evaluation_result = await rule.evaluate(prompt_value, answer)
        else:
            evaluation_result = await asyncio.to_thread(rule.evaluate, prompt_value, answer)
        
        is_pass = evaluation_result.get("is_pass", False)
        feedback = evaluation_result.get("feedback", "")
        no_retry = evaluation_result.get("no_retry", False)
        
        if not is_pass:
            logger.error(f"❌ Rule {i+1} failed: {feedback}")
            return (is_pass, feedback, no_retry)
    
    return (True, "", False)

def _execute_rules_sync(rules, prompt_value, answer):
    """Execute a list of rules sequentially synchronously
    
    Args:
        rules: A single BaseRule or list of BaseRule objects
        prompt_value: The original user prompt
        answer: The model's answer
        
    Returns:
        tuple: (is_pass, feedback, no_retry)
    """
    # Convert single rule to list
    rule_list = rules if isinstance(rules, list) else [rules]
    
    for i, rule in enumerate(rule_list):
        logger.info(f"Executing rule {i+1}/{len(rule_list)}...")
        evaluation_result = rule.evaluate(prompt_value, answer)
        
        is_pass = evaluation_result.get("is_pass", False)
        feedback = evaluation_result.get("feedback", "")
        no_retry = evaluation_result.get("no_retry", False)
        
        if not is_pass:
            logger.error(f"❌ Rule {i+1} failed: {feedback}")
            return (is_pass, feedback, no_retry)
    
    return (True, "", False)

def verify(user_prompt=None, rules=None, max_retries=2, on_fail=ReturnBest(), config=None):
    # Handle config parameter
    if config:
        max_retries = config.max_retries
        on_fail = config.on_fail
        rules = config.rules
    
    def decorator(func):
        # Check if the function is async
        is_async = inspect.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                prompt_value, arg_index = _get_prompt_value(user_prompt, args, kwargs)
                
                retry_count = 0
                best_answer = None
                current_prompt = prompt_value
                
                while retry_count <= max_retries:
                    if retry_count == 0:
                        logger.info("Generating initial answer...")
                    else:
                        logger.warning(f"Triggering reflection and rewrite, attempt {retry_count}...")
                    
                    new_args, new_kwargs = _update_prompt(current_prompt, arg_index, args, kwargs, user_prompt)
                    answer = await func(*new_args, **new_kwargs)
                    best_answer = answer
                    
                    logger.info("Evaluating answer quality...")
                    is_pass, feedback, no_retry = await _execute_rules_async(rules, prompt_value, answer)
                    
                    if is_pass:
                        if retry_count > 0:
                            logger.info("✅ Correction successful, returning the verified answer!")
                        else:
                            logger.info("✅ Initial draft is flawless, passing through!")
                        return answer
                    
                    if no_retry:
                        logger.warning("Validation error requires no retry, executing fallback strategy.")
                        break
                    
                    current_prompt = _generate_reflection_prompt(prompt_value, best_answer, feedback)
                    retry_count += 1
                
                logger.warning("Maximum retries reached, executing fallback strategy.")
                action_instance = on_fail() if isinstance(on_fail, type) else on_fail
                if inspect.iscoroutinefunction(action_instance.execute):
                    return await action_instance.execute(
                        prompt=prompt_value, 
                        last_answer=best_answer, 
                        feedback=feedback
                    )
                else:
                    return action_instance.execute(
                        prompt=prompt_value, 
                        last_answer=best_answer, 
                        feedback=feedback
                    )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                prompt_value, arg_index = _get_prompt_value(user_prompt, args, kwargs)
                
                retry_count = 0
                best_answer = None
                current_prompt = prompt_value
                
                while retry_count <= max_retries:
                    if retry_count == 0:
                        logger.info("Generating initial answer...")
                    else:
                        logger.warning(f"Triggering reflection and rewrite, attempt {retry_count}...")
                    
                    new_args, new_kwargs = _update_prompt(current_prompt, arg_index, args, kwargs, user_prompt)
                    answer = func(*new_args, **new_kwargs)
                    best_answer = answer
                    
                    logger.info("Evaluating answer quality...")
                    is_pass, feedback, no_retry = _execute_rules_sync(rules, prompt_value, answer)
                    
                    if is_pass:
                        if retry_count > 0:
                            logger.info("✅ Correction successful, returning the verified answer!")
                        else:
                            logger.info("✅ Initial draft is flawless, passing through!")
                        return answer
                    
                    if no_retry:
                        logger.warning("Validation error requires no retry, executing fallback strategy.")
                        break
                    
                    current_prompt = _generate_reflection_prompt(prompt_value, best_answer, feedback)
                    retry_count += 1
                
                logger.warning("Maximum retries reached, executing fallback strategy.")
                action_instance = on_fail() if isinstance(on_fail, type) else on_fail
                return action_instance.execute(
                    prompt=prompt_value, 
                    last_answer=best_answer, 
                    feedback=feedback
                )
            return sync_wrapper
    return decorator

# Add config method to verify function
verify.config = Config