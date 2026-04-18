import {
  FallbackAction,
  ReturnBest,
  RaiseError,
  ReturnSafeMessage,
} from "./core/actions.js";
import { BaseRule, LLMJudge, Web_LLMJudge, CustomJudge } from "./core/rules.js";
import { verify } from "./core/verify.js";
import { Config } from "./core/config.js";

// Export components
const actions = {
  ReturnBest,
  RaiseError,
  ReturnSafeMessage,
  FallbackAction,
};

const rules = {
  BaseRule,
  LLMJudge,
  Web_LLMJudge,
  CustomJudge,
};

export { verify, rules, actions, Config };
export default { verify, rules, actions, Config };
