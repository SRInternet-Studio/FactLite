from abc import ABC, abstractmethod
import openai
from ddgs import DDGS
import ddgs.exceptions as ddgs_exceptions
import json
import inspect

class BaseRule(ABC):
    """Base rules class for all judge implementations"""
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
            with DDGS(proxy=self.proxy) if self.proxy else DDGS() as ddgs:
                search_results = list(ddgs.text(query=user_prompt, backend=self.backend, max_results=self.max_results))
        except ddgs_exceptions.DDGSException as e:
            return {"is_pass": False, "feedback": f"Error searching the web: {e}", "no_retry": True}
            
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
            else:
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a fact-checking judge. Return only JSON output."},
                        {"role": "user", "content": evaluation_prompt}
                    ]
                )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "is_pass": False,
                "feedback": f"Web_LLMJudge API call failed: {str(e)}. Please check your API key and network connection.",
                "no_retry": True
            }
            
class LLMJudge(BaseRule):
    def __init__(self, model="gpt-4o-mini", api_key=None, base_url=None):
        """Initialize LLMJudge with OpenAI API key
        
        Args:
            model (str): OpenAI model to use for evaluation
            api_key (str): OpenAI API key (defaults to global openai.api_key)
            base_url (str): OpenAI API base URL (defaults to global openai.api_url)
        """
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
            else:
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a fact-checking judge. Return only JSON output."},
                        {"role": "user", "content": evaluation_prompt}
                    ]
                )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "is_pass": False,
                "feedback": f"LLMJudge API call failed: {str(e)}. Please check your API key and network connection.",
                "no_retry": True
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
        
        sig = inspect.signature(eval_func)
        params = sig.parameters.values()
        if not (any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params) or len(params) >= 2):
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
            result = self.eval_func(user_prompt, answer)
            
            if not isinstance(result, dict) or "is_pass" not in result or "feedback" not in result or \
               not isinstance(result["is_pass"], bool) or not isinstance(result["feedback"], str):
                raise ValueError("eval_func must return a dict with 'is_pass' (bool) and 'feedback' (str) keys")
            
            return result
        except Exception as e:
            return {
                "is_pass": False,
                "feedback": f"Error in custom judge: {str(e)}. Please fix your evaluation function.",
                "no_retry": True
            }

class RegexValidator(BaseRule):
    def __init__(self, banned_words=None, required_pattern=None, banned_words_file=None):
        """Initialize RegexValidator with banned words and required pattern
        
        Args:
            banned_words (list): List of banned words or patterns
            required_pattern (list): List of regular expression patterns that must be present
            banned_words_file (str): Path to a TXT file containing banned words (one per line)
        """
        import re
        self.banned_words = banned_words or []
        self.required_pattern = required_pattern or []
        self.banned_words_file = banned_words_file
        self.re = re
        
        # Load banned words from file if provided
        if banned_words_file:
            try:
                with open(banned_words_file, 'r', encoding='utf-8') as f:
                    file_words = [line.strip() for line in f if line.strip()]
                self.banned_words.extend(file_words)
            except Exception as e:
                # Store error for evaluation
                self.file_error = e
    
    def evaluate(self, user_prompt, answer):
        """Evaluate the answer using regex patterns
        
        Args:
            user_prompt (str): The original user question
            answer (str): The model's answer
            
        Returns:
            dict: A dictionary with "is_pass" (bool) and "feedback" (str) keys
        """
        # Check for file loading error
        if hasattr(self, 'file_error'):
            return {
                "is_pass": False, 
                "feedback": f"Error loading banned words file: {str(self.file_error)}",
                "no_retry": True
            }
        
        # Check if no banned words provided
        if not self.banned_words and not self.required_pattern:
            return {
                "is_pass": False, 
                "feedback": "No banned words or required pattern provided",
                "no_retry": True
            }
        
        # Check for banned words
        for word in self.banned_words:
            if word.lower() in answer.lower():
                banned_words_str = '", "'.join(self.banned_words)
                return {"is_pass": False, "feedback": f"Answer contains banned word: \"{word}\". The words \"{banned_words_str}\" are not allowed in the answer. You MUST use synonyms or alternative descriptions instead. (e.g., if 'apple' is banned, use 'the red fruit' or 'that tech company'). Do NOT just delete it, rewrite the sentence to bypass the banned word."}
        
        # Check for required pattern
        for pattern in self.required_pattern:
            if not self.re.search(pattern, answer):
                required_pattern_str = '", "'.join(self.required_pattern)
                return {"is_pass": False, "feedback": f"Answer should contain required pattern: \"{pattern}\" but it does not contain it. The required pattern is \"{required_pattern_str}\". Please **add** them to the answer."}
        
        return {"is_pass": True, "feedback": ""}

class JSONValidator(BaseRule):
    def __init__(self, required_keys=None):
        """Initialize JSONValidator with required keys
        
        Args:
            required_keys (list): List of keys that must be present in the JSON
        """
        self.required_keys = required_keys or []
    
    def evaluate(self, user_prompt, answer):
        """Evaluate if the answer is valid JSON and contains required keys
        
        Args:
            user_prompt (str): The original user question
            answer (str): The model's answer
            
        Returns:
            dict: A dictionary with "is_pass" (bool) and "feedback" (str) keys
        """
        try:
            cleaned_answer = answer.strip()
            if cleaned_answer.startswith("```json"):
                cleaned_answer = cleaned_answer[7:-3].strip()
            elif cleaned_answer.startswith("```"):
                cleaned_answer = cleaned_answer[3:-3].strip()
                
            data = json.loads(cleaned_answer)
            missing_keys = [key for key in self.required_keys if key not in data]
            
            if missing_keys:
                return {"is_pass": False, "feedback": f"JSON missing required keys: {', '.join(missing_keys)}, You must include this key."}
            
            return {"is_pass": True, "feedback": ""}
        except json.JSONDecodeError as e:
            return {"is_pass": False, "feedback": f"Invalid JSON format: {str(e)}. CRITICAL INSTRUCTION: You must output ONLY raw valid JSON content without any additional description."}
        except Exception as e:
            return {"is_pass": False, "feedback": f"Error validating JSON: {str(e)}", "no_retry": True}

class LengthValidator(BaseRule):
    def __init__(self, min_length=None, max_length=None, include_punctuation=True):
        """Initialize LengthValidator with length constraints
        
        Args:
            min_length (int): Minimum length of the answer
            max_length (int): Maximum length of the answer
            include_punctuation (bool): Whether to include punctuation in length calculation
        """
        self.min_length = min_length
        self.max_length = max_length
        self.include_punctuation = include_punctuation
    
    def evaluate(self, user_prompt, answer):
        """Evaluate the answer length
        
        Args:
            user_prompt (str): The original user question
            answer (str): The model's answer
            
        Returns:
            dict: A dictionary with "is_pass" (bool) and "feedback" (str) keys
        """
        try:
            # Calculate length
            if not self.include_punctuation:
                import string
                cleaned_answer = ''.join([c for c in answer if c not in string.punctuation])
                length = len(cleaned_answer)
            else:
                length = len(answer)
            
            # Check min length
            if self.min_length is not None and length < self.min_length:
                return {"is_pass": False, "feedback": f"Answer is too short. Minimum length: {self.min_length}, actual: {length}. CRITICAL INSTRUCTION: You must extend the content to meet the minimum length {self.min_length}."}
            
            # Check max length
            if self.max_length is not None and length > self.max_length:
                return {"is_pass": False, "feedback": f"Answer is too long. Maximum length: {self.max_length}, actual: {length}. CRITICAL INSTRUCTION: You must drastically cut the content! Remove all filler words, greetings, and examples. Summarize the core point in MAXIMUM 3 short sentences. Do not exceed this!"}
            
            return {"is_pass": True, "feedback": ""}
        except Exception as e:
            return {
                "is_pass": False, 
                "feedback": f"Error validating length: {str(e)}",
                "no_retry": True
            }

class ModerationJudge(BaseRule):
    def __init__(self, api_key=None, base_url=None):
        """Initialize ModerationJudge with OpenAI API key
        
        Args:
            api_key (str): OpenAI API key (defaults to global openai.api_key)
            base_url (str): OpenAI API base URL (defaults to global openai.api_url)
            
        Important: The Moderation API is only officially supported by OpenAI. If your global base_url is from another provider (such as DeepSeek), please explicitly pass in base_url="https://api.openai.com/v1" or a proxy address here.
        """
        self.base_url = base_url
        api_key = api_key or openai.api_key
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url) if hasattr(openai, "OpenAI") else openai
    
    def evaluate(self, user_prompt, answer):
        """Evaluate the answer using OpenAI Moderation API
        
        Args:
            user_prompt (str): The original user question
            answer (str): The model's answer
            
        Returns:
            dict: A dictionary with "is_pass" (bool) and "feedback" (str) keys
        """
        try:
            # Call OpenAI Moderation API
            if hasattr(openai, "OpenAI"):
                response = self.client.moderations.create(input=answer)
                result = response.results[0]
            else:
                response = self.client.Moderation.create(input=answer)
                result = response["results"][0]
            
            # Check if flagged
            if getattr(result, 'flagged', False) or (isinstance(result, dict) and result.get("flagged")):
                # Collect violated categories
                categories = getattr(result, 'categories', result.get('categories', {}))
                if isinstance(categories, dict):
                    violated =[k for k, v in categories.items() if v]
                else:
                    violated =[k for k, v in categories.model_dump().items() if v]
                
                feedback = f"Content violates OpenAI's usage policies in the following categories: {', '.join(violated)}. Please review the content and modify it accordingly."
                return {"is_pass": False, "feedback": feedback}
            
            # No violations
            return {"is_pass": True, "feedback": ""}
        except Exception as e:
            return {
                "is_pass": False,
                "feedback": f"Moderation API call failed: {str(e)}. Please check your API key and network connection.",
                "no_retry": True
            }