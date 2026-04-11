## 1.0.1

* Initial release of FactLite for Dart/Flutter.
* Core `verify()` function with Generate -> Evaluate -> Reflect loop.
* `LLMJudge` — Accepts user-provided `ChatCompletionFunction` to evaluate answers via any LLM.
* `CustomJudge` — Custom evaluation function support (sync & async).
* `FactLiteConfig` — Configuration object for rule, retries, and fallback.
* `VerifiedGenerator` — Reusable wrapper for binding config to a generator.
* Fallback actions: `ReturnBest`, `RaiseError`, `ReturnSafeMessage`.
* `EvaluationResult` type-safe evaluation result class.
