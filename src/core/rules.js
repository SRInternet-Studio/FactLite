import OpenAI from "openai";

/**
 * Base rule class for all judge implementations.
 * @abstract
 */
class BaseRule {
  /**
   * Evaluate the answer against the user prompt.
   * @param {string} userPrompt - The original user question
   * @param {string} answer - The model's answer
   * @returns {Promise<{is_pass: boolean, feedback: string}>}
   */
  async evaluate(userPrompt, answer) {
    throw new Error("Subclasses must implement evaluate method");
  }
}

/**
 * A Web-enhanced LLM judge that uses web search + OpenAI API to evaluate answers.
 */
class Web_LLMJudge extends BaseRule {
  /**
   * @param {object} options
   * @param {string} [options.model="gpt-4o-mini"] - The OpenAI model to use
   * @param {string} [options.apiKey] - The OpenAI API key
   * @param {string} [options.baseURL] - The OpenAI API base URL
   * @param {number} [options.maxResults=3] - Max web search results
   * @param {string} [options.proxy] - Proxy for web search
   * @param {string} [options.backend="duckduckgo"] - Search backend
   */
  constructor({
    model = "gpt-4o-mini",
    apiKey,
    baseURL,
    maxResults = 3,
    proxy,
    backend = "duckduckgo",
  } = {}) {
    super();
    this.model = model;
    this.backend = backend;
    this.baseURL = baseURL;
    this.maxResults = maxResults;
    this.proxy = proxy;
    this.client = new OpenAI({ apiKey, baseURL });
  }

  async evaluate(userPrompt, answer) {
    let searchResults;
    try {
      // Dynamic import for duck-duck-scrape
      const { search } = await import("duck-duck-scrape");
      const results = await search(userPrompt, {
        safeSearch: 0,
      });
      searchResults = results.results.slice(0, this.maxResults);
    } catch (e) {
      return {
        is_pass: false,
        feedback: `Error searching the web: ${e.message}`,
      };
    }

    if (!searchResults || searchResults.length === 0) {
      return {
        is_pass: false,
        feedback: "Can not find any relevant information on the web.",
      };
    }

    const context = searchResults
      .map((res) => `- ${res.description || res.snippet || ""}`)
      .join("\n");

    const evaluationPrompt = `You are a fact-checking judge. Please ** use only the [web search] provided below ** to check if the [AI's answer] contains factual errors, fabricated years, or non-existent entities. Return a JSON object with two fields:
- is_pass: boolean indicating if the response is factually correct
- feedback: detailed criticism if is_pass is false, or empty string if true

[web search]
${context}

[User question]: ${userPrompt}
[AI's answer]: ${answer}

JSON output:`;

    try {
      const response = await this.client.chat.completions.create({
        model: this.model,
        messages: [
          {
            role: "system",
            content:
              "You are a fact-checking judge. Return only JSON output.",
          },
          { role: "user", content: evaluationPrompt },
        ],
        response_format: { type: "json_object" },
      });
      const resultStr = response.choices[0].message.content;
      return JSON.parse(resultStr);
    } catch (e) {
      return {
        is_pass: false,
        feedback: `Web_LLMJudge API call failed: ${e.message}. Please check your API key and network connection.`,
      };
    }
  }
}

/**
 * An LLM-based judge that uses OpenAI API to evaluate answers.
 */
class LLMJudge extends BaseRule {
  /**
   * @param {object} options
   * @param {string} [options.model="gpt-4o-mini"] - The OpenAI model to use
   * @param {string} [options.apiKey] - The OpenAI API key
   * @param {string} [options.baseURL] - The OpenAI API base URL
   */
  constructor({ model = "gpt-4o-mini", apiKey, baseURL } = {}) {
    super();
    this.model = model;
    this.baseURL = baseURL;
    this.client = new OpenAI({ apiKey, baseURL });
  }

  async evaluate(userPrompt, answer) {
    const evaluationPrompt = `You are a fact-checking judge. Evaluate the following response to determine if it accurately answers the user's question. Return a JSON object with two fields:
- is_pass: boolean indicating if the response is factually correct
- feedback: detailed criticism if is_pass is false, or empty string if true

User question: ${userPrompt}
Response: ${answer}

JSON output:`;

    try {
      const response = await this.client.chat.completions.create({
        model: this.model,
        messages: [
          {
            role: "system",
            content:
              "You are a fact-checking judge. Return only JSON output.",
          },
          { role: "user", content: evaluationPrompt },
        ],
        response_format: { type: "json_object" },
      });
      const resultStr = response.choices[0].message.content;
      return JSON.parse(resultStr);
    } catch (e) {
      return {
        is_pass: false,
        feedback: `LLMJudge API call failed: ${e.message}. Please check your API key and network connection.`,
      };
    }
  }
}

/**
 * A custom judge that uses a user-provided evaluation function.
 */
class CustomJudge extends BaseRule {
  /**
   * @param {Function} evalFunc - A function that takes (userPrompt, answer) and returns {is_pass: boolean, feedback: string}
   */
  constructor(evalFunc) {
    super();
    if (typeof evalFunc !== "function") {
      throw new TypeError("evalFunc must be a function");
    }
    if (evalFunc.length < 2) {
      throw new Error(
        "evalFunc must accept at least two parameters: userPrompt and answer"
      );
    }
    this.evalFunc = evalFunc;
  }

  async evaluate(userPrompt, answer) {
    try {
      // Support both sync and async eval functions
      let result = this.evalFunc(userPrompt, answer);
      if (result instanceof Promise) {
        result = await result;
      }

      // Validate the result
      if (typeof result !== "object" || result === null) {
        throw new Error("evalFunc must return an object");
      }
      if (!("is_pass" in result)) {
        throw new Error("Returned object must contain 'is_pass' key");
      }
      if (!("feedback" in result)) {
        throw new Error("Returned object must contain 'feedback' key");
      }
      if (typeof result.is_pass !== "boolean") {
        throw new Error("'is_pass' must be a boolean");
      }
      if (typeof result.feedback !== "string") {
        throw new Error("'feedback' must be a string");
      }

      return result;
    } catch (e) {
      return {
        is_pass: false,
        feedback: `Error in custom judge: ${e.message}. Please fix your evaluation function.`,
      };
    }
  }
}

export { BaseRule, LLMJudge, Web_LLMJudge, CustomJudge };
