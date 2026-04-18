import { ReturnBest } from "./actions.js";
import { Config } from "./config.js";

/**
 * Format a timestamp in HH:MM:SS format.
 * @returns {string}
 */
function timestamp() {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

/**
 * Generate a reflection prompt for the LLM to self-correct.
 * @param {string} promptValue - The original user question
 * @param {string} bestAnswer - The model's last answer
 * @param {string} feedback - The judge's feedback
 * @returns {string}
 */
function generateReflectionPrompt(promptValue, bestAnswer, feedback) {
  return `[System Prompt: You need to self-reflect and self-correct]
Original user question: ${promptValue}
Your previous answer: ${bestAnswer}
Judge's feedback: ${feedback}
Please take a deep breath, strictly correct the errors mentioned above, and provide the final perfect answer.`;
}

/**
 * Create a verified wrapper around an async function.
 *
 * In Node.js, since there are no decorators like Python, `verify` returns a higher-order
 * function that wraps the target function with an automated Generate -> Evaluate -> Reflect loop.
 *
 * @param {object} options
 * @param {string} [options.userPrompt] - The name of the parameter that contains the user prompt, or unused if promptIndex is used
 * @param {import('./rules.js').BaseRule} [options.rule] - The rule to use for evaluation
 * @param {number} [options.maxRetries=2] - Maximum number of retries
 * @param {import('./actions.js').FallbackAction} [options.onFail] - The fallback action on failure
 * @param {Config} [options.config] - A Config object (overrides rule, maxRetries, onFail)
 * @returns {function} A higher-order function that wraps the target function
 */
function verify({
  userPrompt,
  rule,
  maxRetries = 2,
  onFail = new ReturnBest(),
  config,
} = {}) {
  // Handle config parameter
  if (config) {
    maxRetries = config.maxRetries;
    onFail = config.onFail;
    rule = config.rule;
  }

  /**
   * @param {Function} fn - The async function to wrap. It must accept a prompt string as its first argument.
   * @returns {Function} The wrapped function with verification logic
   */
  return function (fn) {
    /**
     * The wrapped function with verification loop.
     * The first argument is treated as the user prompt.
     * @param {...any} args
     * @returns {Promise<string>}
     */
    async function wrapper(...args) {
      const promptValue = args[0];
      let retryCount = 0;
      let bestAnswer = null;
      let currentPrompt = promptValue;
      let feedback = "";

      while (retryCount <= maxRetries) {
        if (retryCount === 0) {
          console.log(`${timestamp()} - [FactLite] - Generating initial answer...`);
        } else {
          console.warn(
            `${timestamp()} - [FactLite] - Triggering reflection and rewrite, attempt ${retryCount}...`
          );
        }

        // Replace the first argument with the current (possibly reflected) prompt
        const newArgs = [currentPrompt, ...args.slice(1)];
        const answer = await fn(...newArgs);
        bestAnswer = answer;

        console.log(`${timestamp()} - [FactLite] - Evaluating answer quality...`);
        const evaluationResult = await rule.evaluate(promptValue, answer);
        const isPass = evaluationResult.is_pass || false;
        feedback = evaluationResult.feedback || "";

        if (isPass) {
          if (retryCount > 0) {
            console.log(
              `${timestamp()} - [FactLite] - ✅ Correction successful, returning the verified answer!`
            );
          } else {
            console.log(
              `${timestamp()} - [FactLite] - ✅ Initial draft is flawless, passing through!`
            );
          }
          return answer;
        }

        console.error(
          `${timestamp()} - [FactLite] - ❌ Hallucination or error detected: ${feedback}`
        );

        currentPrompt = generateReflectionPrompt(
          promptValue,
          bestAnswer,
          feedback
        );
        retryCount++;
      }

      console.warn(
        `${timestamp()} - [FactLite] - Maximum retries reached, executing fallback strategy.`
      );

      const actionInstance =
        typeof onFail === "function" ? new onFail() : onFail;
      return actionInstance.execute(promptValue, bestAnswer, feedback);
    }

    return wrapper;
  };
}

// Attach config constructor to verify
verify.config = function (options) {
  return new Config(options);
};

export { verify };
