## 1.1.0

* Added `WebLLMJudge` — A web-enhanced judge that leverages web search results to verify answers against the latest information.
  * Accepts a user-provided `WebSearchFunction` for framework-agnostic web search integration.
  * Configurable `maxResults` for controlling the number of search results used.
  * Seamless integration with existing FactLite workflow.
* Added `WebSearchFunction` type definition.

## 1.0.1

* Initial release of FactLite for Dart/Flutter.
* Core `verify()` function with Generate -> Evaluate -> Reflect loop.
* `LLMJudge` — Accepts user-provided `ChatCompletionFunction` to evaluate answers via any LLM.
* `CustomJudge` — Custom evaluation function support (sync & async).
* `FactLiteConfig` — Configuration object for rule, retries, and fallback.
* `VerifiedGenerator` — Reusable wrapper for binding config to a generator.
* Fallback actions: `ReturnBest`, `RaiseError`, `ReturnSafeMessage`.
* `EvaluationResult` type-safe evaluation result class.
