import { ReturnBest } from "./actions.js";

/**
 * Configuration for the FactLite framework.
 */
class Config {
  /**
   * @param {object} options
   * @param {import('./rules.js').BaseRule} [options.rule] - The rule to use for evaluation
   * @param {number} [options.maxRetries=2] - Maximum number of retries
   * @param {import('./actions.js').FallbackAction} [options.onFail] - The fallback action on failure
   */
  constructor({ rule = null, maxRetries = 2, onFail = new ReturnBest() } = {}) {
    this.rule = rule;
    this.maxRetries = maxRetries;
    this.onFail = onFail;
  }
}

export { Config };
