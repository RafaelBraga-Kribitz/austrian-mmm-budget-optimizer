# 08 — DESIGN PATTERNS (where each belongs)

Each pattern below is prescribed for specific locations. Using a pattern where it is
not prescribed is not forbidden — but check [09_ANTI_PATTERNS.md](09_ANTI_PATTERNS.md)
(over-engineering) first: this codebase is deliberately small and explicit.

| Pattern | Where it belongs | Why there |
|---|---|---|
| **Functional Core / Imperative Shell** | The governing pattern everywhere: pure computation (`transforms`, `dgp`, `recovery` metrics, `optimizer` objective, `elicit`, `format`) wrapped by thin IO shells (CLI runners, `posterior_io`, report writers, dbt) | Determinism gates (SIM-070, DC-703, VR-701) are only achievable when all randomness/IO is at the edges |
| **Pure functions** | All math: `adstock_recursive`, `hill`, `season_index`, `adstock_convolve`, `hill_saturation`, scaling pair, elicitation converters, gain metric, HC1 | Property-testable; the recovery argument rests on these being right |
| **Configuration Objects** | `Settings`, `ScenarioConfig`, `PriorConfig`, `DiagGates`, `AllocationConstraints`, `IntakeManifest`, `TruthFile` — pydantic, `extra='forbid'`, frozen where possible | EB-040; validation at the boundary; spec tables become schema-checked data |
| **Repository (data access)** | `common/db.py` as the single mart doorway (AD-030); `posterior_io` as the single posterior doorway | One contract to test; model/decide/report stay storage-agnostic |
| **Factory** | `DiagGates.standard()` / `DiagGates.layer_r()`; `AllocationConstraints` built by one factory from mart + settings; `build_model` itself is a model factory (MD-002) | Named constructors make the *choice* explicit and greppable (MD-074 must never be auto-selected) |
| **Strategy** | Fit variants (`flat`, `nopromo`, `loco-<ch>`, `holdout`) as data-selection/prior-selection strategies inside `model/fit.py` — one runner, parameterized | VR-5xx needs many fits differing in exactly one dimension; strategy keeps them from forking the pipeline |
| **Builder** | `pm.Model` construction in `mmm.py`: assemble design matrices → priors → likelihood step-by-step inside one function (not a class hierarchy) | The model is the product; the builder signature is the spec (MD-002) |
| **Dependency Injection** | Pass `Settings`, `PriorConfig`, `ScaleFactors`, RNG `Generator`, and connections as arguments; construct them only in shells (CLI/main) | Testability without patching; no hidden state ([09 §A-5](09_ANTI_PATTERNS.md)) |
| **Pipeline** | Makefile targets as the pipeline spine (simulate→transform→fit→recover→decide→ssot→export→report); each stage reads/writes artifacts, no in-memory handoffs across stages | Restartability; VR-703's no-sampling regeneration falls out of artifact-passing |
| **Registry** | Export writer (`export_marts.py` file registry, AD-050); SSOT fragment producers (Guide §6) | Additive extension without copy-paste scripts |
| **Template Method (text)** | RECOVERY_REPORT verdict/closing, DC-504 paragraph, EXEC_SUMMARY skeleton: fixed templates with numeric slots | VR §8.1 "no free-form spin"; keeps generated prose SSOT-consistent |
| **Atomic write / temp+rename** | `posterior_io`, truth writer, export writer, SSOT writer | EB-050 — interrupted runs never leave partial artifacts |
| **Retry (bounded, prescribed)** | ONLY the MD-073 reparameterization ladder (rung-by-rung, ADR past rung 1) and DC-204 solver restarts (20, seeded) | Retries elsewhere would mask nondeterminism; these two are the sanctioned forms |
| **Guard clause / fail-fast** | Intake env-var check (AG-020), db.py contract assertions, posterior loader metadata refusal, gate runners | Errors surface at the richest-context boundary |
| **Caching** | Committed thinned posteriors ARE the cache (MD-051/VR-703); pytensor compiledir cache in CI (BP-D-17); `load_settings()` memoized | Only sanctioned caches — no ad-hoc memoization of scientific results ([09 §A-12](09_ANTI_PATTERNS.md)) |
| **State machine (implicit, enforced)** | Project phase state encoded in git history and checked by `check_layer_order.py` (recovery→freeze→fit as ordered states) | The argument of the repo is a state sequence; the checker is its transition guard |
| **Composition over inheritance** | Everywhere. Class hierarchies are absent by design — dataclasses/pydantic models + functions. The only inheritance: pydantic BaseModel/BaseSettings, logging.Filter | Small codebase; behavior variation comes from data (configs, variants), not subclasses |

**Patterns deliberately NOT used** (do not introduce): ORM layers, plugin systems,
event buses, async, dependency-injection containers/frameworks, abstract base
classes for "future flexibility", microservice/service-layer splits. This is a
batch scientific pipeline; the Makefile is the orchestrator; anything fancier is
[09 §A-13](09_ANTI_PATTERNS.md) over-engineering. Circuit breakers do not apply
(no external services exist — EB-070).
