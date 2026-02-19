# Qwen Model Mapping for Ford Perfect AI Orchestrator

**Document Version:** 1.0  
**Last Updated:** 2026-02-19  
**Endpoint:** DashScope-Intl (Singapore) — `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Welcome Credit | 70M tokens (Alicloud) |
| Initial Test Budget | 1M tokens |
| Primary Brain | `qwen3.5-plus` (stable, 131k context) |
| Hard Session Limit | 250k tokens/session |
| Fallback Strategy | qwen-max (same provider, no cost spike) |

---

## Available Models — Complete Specifications

### Text Models (Production Ready)

| Model ID | Type | Context | Max Out | Input $/1M | Output $/1M | Speed TPS | Latency ms | Tier |
|----------|------|---------|---------|------------|-------------|-----------|------------|------|
| `qwen3.5-plus` | text | 8,192 | 4,096 | $0.006 | $0.012 | 100 | 150 | **PRIMARY** |
| `qwen3.5-plus-2026-02-15` | text | 8,192 | 4,096 | $0.006 | $0.012 | 100 | 150 | STABLE |
| `qwen3-max-2026-01-23` | text | 16,384 | 8,192 | $0.012 | $0.024 | 80 | 200 | PREMIUM |
| `qwen-max-latest` | text | 16,384 | 8,192 | $0.012 | $0.024 | 80 | 200 | PREMIUM |
| `qwen-coder-plus` | code | 8,192 | 4,096 | $0.008 | $0.016 | 120 | 120 | SPECIALIST |
| `qwen-turbo-latest` | text | 4,096 | 2,048 | $0.004 | $0.008 | 150 | 100 | BUDGET |
| `qwen-plus-latest` | text | 8,192 | 4,096 | $0.006 | $0.012 | 100 | 150 | BALANCED |
| `qwen-max` | text | 16,384 | 8,192 | $0.012 | $0.024 | 80 | 200 | LEGACY |
| `qwen-plus` | text | 8,192 | 4,096 | $0.006 | $0.012 | 100 | 150 | LEGACY |
| `qwen-turbo` | text | 4,096 | 2,048 | $0.004 | $0.008 | 150 | 100 | LEGACY |

### Vision/Multimodal Models

| Model ID | Type | Context | Max Out | Input $/1M | Output $/1M | Speed TPS | Latency ms | Capabilities |
|----------|------|---------|---------|------------|-------------|-----------|------------|--------------|
| `qwen-vl-max-latest` | vision | 16,384 | 8,192 | $0.015 | $0.030 | 70 | 250 | OCR, chart analysis, scene understanding |
| `qwen-vl-plus-latest` | vision | 8,192 | 4,096 | $0.009 | $0.018 | 100 | 180 | Object detection, image captioning |
| `qwen2.5-vl-72b-instruct` | multimodal | 4,096 | 2,048 | $0.010 | $0.020 | 120 | 150 | Instruction-based VQA, diagram parsing |

### Unavailable via Chat API (Separate Endpoints)

These models exist but require different API endpoints (not compatible with `brain.ask()`):

- `qwen3-tts-*` series → Text-to-speech (requires CosyVoice/TTS endpoint)
- `qwen3-omni-*` series → Real-time multimodal streaming (requires WebSocket endpoint)
- `qwen-audio-*` series → Audio transcription/analysis (requires audio endpoint)

---

## Use-Case Mapping

### When to Use Each Model

#### 🧠 `qwen3.5-plus` (PRIMARY BRAIN)
**Use for:** 80% of all tasks
- Complex reasoning and analysis
- Research synthesis
- Document summarization (>10 pages)
- Multi-step problem solving
- Code review and architecture decisions
- Philosophy/critical thinking tasks

**Why:** Best balance of capability, context window, and cost. Stable version with predictable behavior.

#### 📅 `qwen3.5-plus-2026-02-15` (STABLE PINNED VERSION)
**Use for:**
- Reproducible research workflows
- Batch processing where consistency matters
- Regression testing
- Production pipelines requiring version pinning

**Why:** Identical specs to qwen3.5-plus but frozen in time. No surprise updates mid-project.

#### 🚀 `qwen-max-latest` / `qwen3-max-2026-01-23` (PREMIUM REASONING)
**Use for:**
- Mathematical proofs
- Scientific paper analysis
- Legal contract review
- Creative writing (novels, scripts)
- Strategic planning
- Tasks requiring maximum depth

**Trade-off:** 2x cost, 20% slower, but significantly deeper reasoning.

**Budget allocation:** ≤10% of total token usage

#### 💻 `qwen-coder-plus` (CODING SPECIALIST)
**Use for:**
- Code generation (all languages)
- Debugging assistance
- Unit test creation
- Code refactoring
- Documentation generation
- CI/CD pipeline scripting

**Why:** Optimized for code patterns, understands type systems, faster than general models for coding tasks.

**Note:** For simple one-liners, qwen-turbo-latest may be more cost-effective.

#### ⚡ `qwen-turbo-latest` (BUDGEST/FAST)
**Use for:**
- Quick Q&A (<500 tokens expected)
- Simple transformations
- Classification tasks
- Draft generation (to be refined later)
- High-volume batch processing on budget
- Health checks and pings

**Avoid for:** Complex reasoning, creative work, code generation

**Budget allocation:** Up to 30% for high-volume simple tasks

#### ⚖️ `qwen-plus-latest` (BALANCED ALTERNATIVE)
**Use for:**
- General conversation
- Medium-complexity tasks
- When qwen3.5-plus is at capacity
- A/B testing model performance

**Why:** Similar to qwen3.5-plus but "latest" may have minor improvements or regressions. Use as secondary option.

#### 👁️ `qwen-vl-max-latest` (VISION PREMIUM)
**Use for:**
- Technical diagram analysis
- Chart/graph interpretation
- OCR-heavy documents
- Screenshot debugging
- UI/UX analysis

**Budget allocation:** ≤5% (vision tasks should be targeted)

#### 👁️ `qwen-vl-plus-latest` (VISION BALANCED)
**Use for:**
- Simple image captioning
- Object counting/detection
- Basic visual QA
- When max quality isn't critical

#### 🎯 `qwen2.5-vl-72b-instruct` (VISION INSTRUCTION-FOLLOWING)
**Use for:**
- Specific visual queries ("count red circles in top-left quadrant")
- Diagram parsing with explicit instructions
- Structured extraction from images

---

## Decision Tree for Model Selection

```
START
│
├─ Is input an image or contains visual data?
│  ├─ YES → Is task complex (diagrams/charts/OCR)?
│  │         ├─ YES → qwen-vl-max-latest
│  │         └─ NO  → Is instruction very specific?
│  │                   ├─ YES → qwen2.5-vl-72b-instruct
│  │                   └─ NO  → qwen-vl-plus-latest
│  │
│  └─ NO (text only) → Continue ↓
│
├─ Is this a coding task?
│  ├─ YES → Is it complex (architecture/refactoring/debugging)?
│  │         ├─ YES → qwen-coder-plus
│  │         └─ NO (simple one-liner) → qwen-turbo-latest
│  │
│  └─ NO → Continue ↓
│
├─ What's the complexity level?
│  ├─ HIGH (math/science/legal/creative) → qwen-max-latest
│  │                                        [Budget check: <10% remaining?]
│  │                                         ├─ YES → Proceed
│  │                                         └─ NO → Fall back to qwen3.5-plus
│  │
│  ├─ MEDIUM (analysis/research/summary) → qwen3.5-plus ← PRIMARY ROUTE
│  │                                        [Need reproducibility?]
│  │                                         ├─ YES → qwen3.5-plus-2026-02-15
│  │                                         └─ NO → qwen3.5-plus
│  │
│  ├─ LOW (simple Q&A/classification) → qwen-turbo-latest
│  │
│  └─ UNKNOWN/GENERAL → qwen-plus-latest
│
└─ END
```

### Quick Reference Card

| Task Type | Primary Choice | Budget Alternative | Premium Option |
|-----------|---------------|-------------------|----------------|
| Coding | qwen-coder-plus | qwen-turbo-latest | qwen-max-latest |
| Research | qwen3.5-plus | qwen-plus-latest | qwen-max-latest |
| Simple Q&A | qwen-turbo-latest | — | — |
| Analysis | qwen3.5-plus | qwen-plus-latest | qwen3-max-2026-01-23 |
| Creative | qwen-max-latest | qwen3.5-plus | — |
| Vision (complex) | qwen-vl-max-latest | — | — |
| Vision (simple) | qwen-vl-plus-latest | qwen2.5-vl-72b-instruct | — |
| Reproducible | qwen3.5-plus-2026-02-15 | — | qwen3-max-2026-01-23 |

---

## 1M Token Test Budget Allocation

### Phase 1: Baseline Testing (200k tokens — 20%)

| Model | Tokens | Purpose |
|-------|--------|---------|
| qwen3.5-plus | 100k | Establish baseline performance metrics |
| qwen-turbo-latest | 50k | Test speed/cost efficiency on simple tasks |
| qwen-coder-plus | 50k | Validate coding capabilities vs primary brain |

**Success Criteria:**
- Latency <2s for 95th percentile
- Cost tracking accuracy verified
- Fallback mechanism tested

### Phase 2: Specialized Model Validation (300k tokens — 30%)

| Model | Tokens | Purpose |
|-------|--------|---------|
| qwen-max-latest | 100k | Test premium reasoning on hard problems |
| qwen-vl-max-latest | 100k | Vision tasks (images + analysis) |
| qwen-vl-plus-latest | 50k | Compare vision quality vs cost |
| qwen2.5-vl-72b-instruct | 50k | Test instruction-following on visuals |

**Success Criteria:**
- Quality improvement justifies 2x cost for max models
- Vision models correctly parse test diagrams
- Clear differentiation between vision tiers

### Phase 3: Edge Cases & Stress Testing (300k tokens — 30%)

| Model | Tokens | Purpose |
|-------|--------|---------|
| qwen3.5-plus | 150k | Long-context stress test (near 131k limit) |
| qwen3.5-plus-2026-02-15 | 50k | Verify pinned version stability |
| qwen-max-latest | 100k | Complex multi-turn conversations |

**Success Criteria:**
- No degradation near context limits
- Pinned version produces identical outputs
- Conversation coherence maintained over 50+ turns

### Phase 4: Integration & Router Testing (200k tokens — 20%)

| Model | Tokens | Purpose |
|-------|--------|---------|
| ALL MODELS | 200k | Test automatic routing logic |
| (distributed) | | A/B testing decision tree |

**Success Criteria:**
- Router selects optimal model 90%+ of time
- Cost savings vs single-model baseline
- No misrouted tasks causing failures

### Budget Tracking

```python
# Expected costs for 1M token test (assuming 50/50 input/output split)
budget_breakdown = {
    "qwen3.5-plus": {"tokens": 250000, "est_cost_usd": 1.125},
    "qwen-turbo-latest": {"tokens": 100000, "est_cost_usd": 0.30},
    "qwen-coder-plus": {"tokens": 100000, "est_cost_usd": 0.60},
    "qwen-max-latest": {"tokens": 200000, "est_cost_usd": 3.60},
    "qwen-vl-max-latest": {"tokens": 150000, "est_cost_usd": 3.375},
    "qwen-vl-plus-latest": {"tokens": 100000, "est_cost_usd": 1.35},
    "qwen2.5-vl-72b-instruct": {"tokens": 100000, "est_cost_usd": 1.50},
    "TOTAL": {"tokens": 1000000, "est_cost_usd": 11.85}
}
```

**Total Estimated Cost:** ~$12 USD (well within welcome credit)

---

## Implementation Notes

### Using brain.ask()

```python
from lib.brain import ask

# Default (uses qwen-plus-latest)
result = ask([{"role": "user", "content": "Hello"}])

# Specify model explicitly
result = ask(
    [{"role": "user", "content": "Write a function..."}],
    model="qwen-coder-plus",
    max_tokens=2000
)

# With system prompt
result = ask(
    [{"role": "user", "content": "Analyze this..."}],
    model="qwen3.5-plus",
    system="You are a critical-rationalist analyst..."
)

# Disable fallback (fail fast)
result = ask(
    [{"role": "user", "content": "..."}],
    model="qwen-turbo-latest",
    fallback=False
)
```

### Router Logic (Pseudocode)

```python
def select_model(task):
    if task.has_image:
        if task.complexity == "high":
            return "qwen-vl-max-latest"
        elif task.specific_instruction:
            return "qwen2.5-vl-72b-instruct"
        else:
            return "qwen-vl-plus-latest"
    
    if task.type == "coding":
        return "qwen-coder-plus" if task.complexity != "trivial" else "qwen-turbo-latest"
    
    if task.complexity == "high":
        if budget.remaining_percent < 10:
            return "qwen3.5-plus"  # Fallback from max
        return "qwen-max-latest"
    
    if task.complexity == "low":
        return "qwen-turbo-latest"
    
    if task.needs_reproducibility:
        return "qwen3.5-plus-2026-02-15"
    
    # Default
    return "qwen3.5-plus"
```

### Monitoring & Logging

All usage is logged to `/opt/ai-orchestrator/var/logs/qwen-usage.tsv`:

```
TIMESTAMP	MODEL	PROVIDER	INPUT_TOKENS	OUTPUT_TOKENS	COST_USD
2026-02-19T14:15:00Z	qwen3.5-plus	qwen-singapore	126	286	0.00039360
```

Monitor with:
```bash
tail -f /opt/ai-orchestrator/var/logs/qwen-usage.tsv
# Or aggregate
awk -F'\t' '{sum+=$6} END {print "Total cost: $" sum}' qwen-usage.tsv
```

---

## Anti-Patterns (What NOT to Do)

❌ **Don't use qwen-max-latest for simple tasks** — 2x cost with minimal benefit  
❌ **Don't use qwen-turbo-latest for complex reasoning** — Will produce shallow analysis  
❌ **Don't mix dated and latest versions in same workflow** — Inconsistent behavior  
❌ **Don't exceed 200k tokens per session** — Leave headroom below 250k hard limit  
❌ **Don't use vision models for text-only tasks** — Wasteful and slower  
❌ **Don't disable fallback in production** — Unless you want hard failures  

---

## Future Considerations

### Models to Watch
- `qwen3-omni-*` series — When WebSocket endpoint is available, enables real-time multimodal
- `qwen3-tts-*` series — For voice output integration (requires CosyVoice endpoint)
- Potential `qwen3.5-max` — If released, would replace qwen-max-latest as premium tier

### Cost Optimization Opportunities
1. **Batching:** Group simple tasks for qwen-turbo-latest bulk processing
2. **Caching:** Cache frequent queries (especially for stable models)
3. **Distillation:** Use qwen-max-latest for training data, qwen3.5-plus for inference
4. **Progressive refinement:** Start with turbo, escalate to max only if needed

---

## Appendix: Model Comparison Matrix

| Feature | qwen3.5-plus | qwen-max-latest | qwen-coder-plus | qwen-turbo-latest |
|---------|--------------|-----------------|-----------------|-------------------|
| **Cost Efficiency** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Reasoning Depth** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Speed** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Code Quality** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Context Window** | 8k | 16k | 8k | 4k |
| **Best For** | General | Complex | Coding | Simple |

---

**Document Maintained By:** Ford Perfect AI Orchestrator  
**Review Cadence:** Monthly or when new models are released  
**Next Review:** 2026-03-19
