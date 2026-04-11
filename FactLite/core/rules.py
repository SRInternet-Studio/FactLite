from abc import ABC, abstractmethod
import openai
from ddgs import DDGS
import ddgs.exceptions as ddgs_exceptions
import json
import inspect

class BaseRule(ABC):
    """Base rule class for all judge implementations"""
    @abstractmethod
    def evaluate(self, user_prompt, answer):
        """Evaluate the answer against the user prompt
        
        Args:
            user_prompt (str): The original user question
            answer (str): The model's answer
            
        Returns:
            dict: A dictionary with "is_pass" (bool) and "feedback" (str) keys
        """
        raise NotImplementedError("Subclasses must implement evaluate method")

class Web_LLMJudge(BaseRule):
    # Note: Assuming the use of the new OpenAI SDK (>=1.0.0)
    def __init__(self, model="gpt-4o-mini", api_key=None, base_url=None, max_results=3, proxy=None, backend="duckduckgo"):
        """ A Web_LLM judge that uses the OpenAI API to evaluate the answer against the user prompt.
        
        Args:
            model (str): The OpenAI model to use for evaluation
            api_key (str): The OpenAI API key to use for the OpenAI API
            base_url (str): The OpenAI API base URL to use for the OpenAI API
            max_results (int): The maximum number of web search results to use for evaluation, defaults to 3.
            proxy (str): The proxy to use for the web search
            backend (str): The backend to use for the web search. You can use "duckduckgo", "bing", "google", defaults to "duckduckgo"
        """
        self.model = model
        self.backend = backend
        self.base_url = base_url
        self.max_results = max_results
        self.proxy = proxy
        api_key = api_key or openai.api_key
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url) if hasattr(openai, "OpenAI") else openai
    
    def evaluate(self, user_prompt, answer):
        try:
            if self.proxy:
                with DDGS(proxy=self.proxy) as ddgs:
                    search_results = list(ddgs.text(query=user_prompt, backend=self.backend, max_results=self.max_results))
            else:
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(query=user_prompt, backend=self.backend, max_results=self.max_results))
        except ddgs_exceptions.DDGSException as e:
            return {"is_pass": False, "feedback": f"Error searching the web: {e}"}
            
        if not search_results:
            return {"is_pass": False, "feedback": "Can not find any relevant information on the web."}
        
        context = "\n".join([f"- {res['body']}" for res in search_results])
        evaluation_prompt = f"""You are a fact-checking judge. Please ** use only the [web search] provided below ** to check if the [AI's answer] contains factual errors, fabricated years, or non-existent entities. Return a JSON object with two fields:
- is_pass: boolean indicating if the response is factually correct
- feedback: detailed criticism if is_pass is false, or empty string if true

[web search]
{context}

[User question]: {user_prompt}
[AI's answer]: {answer}

JSON output:"""
        
        try:
            if hasattr(openai, "OpenAI"):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a fact-checking judge. Return only JSON output."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                result_str = response.choices[0].message.content
            else:
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a fact-checking judge. Return only JSON output."},
                        {"role": "user", "content": evaluation_prompt}
                    ]
                )
                result_str = response.choices[0].message.content
            
            return json.loads(result_str)
        except Exception as e:
            error_message = f"Web_LLMJudge API call failed: {str(e)}. Please check your API key and network connection."
            return {
                "is_pass": False,
                "feedback": error_message
            }
            
class LLMJudge(BaseRule):
    # Note: Assuming the use of the new OpenAI SDK (>=1.0.0)
    def __init__(self, model="gpt-4o-mini", api_key=None, base_url=None):
            self.model = model
            self.base_url = base_url
            api_key = api_key or openai.api_key
            self.client = openai.OpenAI(api_key=api_key, base_url=base_url) if hasattr(openai, "OpenAI") else openai
    
    def evaluate(self, user_prompt, answer):
        evaluation_prompt = f"""You are a fact-checking judge. Evaluate the following response to determine if it accurately answers the user's question. Return a JSON object with two fields:
- is_pass: boolean indicating if the response is factually correct
- feedback: detailed criticism if is_pass is false, or empty string if true

User question: {user_prompt}
Response: {answer}

JSON output:"""
        
        try:
            if hasattr(openai, "OpenAI"):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a fact-checking judge. Return only JSON output."},
                        {"role": "user", "content": evaluation_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                result_str = response.choices[0].message.content
            else:
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a fact-checking judge. Return only JSON output."},
                        {"role": "user", "content": evaluation_prompt}
                    ]
                )
                result_str = response.choices[0].message.content
            
            return json.loads(result_str)
        except Exception as e:
            error_message = f"LLMJudge API call failed: {str(e)}. Please check your API key and network connection."
            return {
                "is_pass": False,
                "feedback": error_message
            }

class CustomJudge(BaseRule):
    def __init__(self, eval_func):
        """Initialize CustomJudge with a custom evaluation function
        
        Args:
            eval_func (callable): A function that takes user_prompt and answer as parameters
                                    and returns a dict with "is_pass" and "feedback" keys
        """
        if not callable(eval_func):
            raise TypeError("eval_func must be a callable")
        
        # Check if the function accepts at least two parameters
        sig = inspect.signature(eval_func)
        params = sig.parameters.values()
        has_var_args = any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params)
        if not has_var_args and len(params) < 2:
            raise ValueError("eval_func must accept at least two parameters: user_prompt and answer")
        
        self.eval_func = eval_func
    
    def evaluate(self, user_prompt, answer):
        """Evaluate the answer using the custom function with error handling
        
        Args:
            user_prompt (str): The original user question
            answer (str): The model's answer
            
        Returns:
            dict: A dictionary with "is_pass" (bool) and "feedback" (str) keys
        """
        try:
            # Call the custom evaluation function
            result = self.eval_func(user_prompt, answer)
            
            # Validate the result
            if not isinstance(result, dict):
                raise ValueError("eval_func must return a dictionary")
            
            if "is_pass" not in result:
                raise ValueError("Returned dictionary must contain 'is_pass' key")
            
            if "feedback" not in result:
                raise ValueError("Returned dictionary must contain 'feedback' key")
            
            if not isinstance(result["is_pass"], bool):
                raise ValueError("'is_pass' must be a boolean")
            
            if not isinstance(result["feedback"], str):
                raise ValueError("'feedback' must be a string")
            
            return result
        except Exception as e:
            # Convert any error to a failed evaluation
            return {
                "is_pass": False,
                "feedback": f"Error in custom judge: {str(e)}. Please fix your evaluation function."
            }