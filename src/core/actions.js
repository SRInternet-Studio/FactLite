/**
 * Base class for all fallback actions.
 * @abstract
 */
class FallbackAction {
  /**
   * Execute the fallback action.
   * @param {string} prompt - The original user question
   * @param {string} lastAnswer - The model's last generated answer
   * @param {string} feedback - The feedback from the judge
   * @returns {string} The fallback action's response
   */
  execute(prompt, lastAnswer, feedback) {
    throw new Error('Subclasses must implement execute method');
  }
}

/**
 * Return the last generated answer despite failing verification.
 */
class ReturnBest extends FallbackAction {
  execute(prompt, lastAnswer, feedback) {
    console.warn('[FactLite] Returning the last generated answer despite failing verification.');
    return lastAnswer;
  }
}

/**
 * Raise an exception if the answer fails verification.
 */
class RaiseError extends FallbackAction {
  execute(prompt, lastAnswer, feedback) {
    console.error('[FactLite] Raising exception due to factual verification failure.');
    throw new Error(`Answer failed factual verification. Last feedback: ${feedback}`);
  }
}

/**
 * Return a safe message if the answer fails verification.
 */
class ReturnSafeMessage extends FallbackAction {
  /**
   * @param {string} [safeMessage="抱歉，AI 暂时无法针对该问题给出有确切把握的回答。"]
   */
  constructor(safeMessage = '抱歉，AI 暂时无法针对该问题给出有确切把握的回答。') {
    super();
    this.safeMessage = safeMessage;
  }

  execute(prompt, lastAnswer, feedback) {
    console.warn(`[FactLite] Returning safe message. Original hallucination feedback: ${feedback}`);
    return this.safeMessage;
  }
}

export { FallbackAction, ReturnBest, RaiseError, ReturnSafeMessage };
