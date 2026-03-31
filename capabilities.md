# RIS Capabilities

A living document describing the current capabilities, behaviors, and architectural components of the **Research Intelligence System (RIS)**.

---

## 1. High-Level Overview
- Purpose of RIS
- Core design philosophy (modular, transparent, multi-model, reproducible)
- Current system maturity level (e.g., v0.1.0 — early architecture)

---

## 2. Core Modules and Responsibilities

### 2.1 Orchestrator
- Routes user requests to appropriate models or tools
- Performs intent detection and context shaping
- Manages multi-step reasoning workflows
- Ensures stability and fallback behavior

### 2.2 Memory Pipeline
- Handles short-term and long-term memory
- Summarization, embedding, retrieval
- Current limitations and planned improvements

### 2.3 Semantic Manager
- Embedding generation and semantic search
- Chunking strategies
- Document ingestion pipeline

### 2.4 Response Governor (planned / in-progress)
- Controls verbosity, tone, and safety
- Generates reasoning traces (post-hoc)
- Enforces consistency across models

---

## 3. Supported Model Capabilities

### 3.1 Language Models
- Model list (Phi-4, etc.)
- Strengths and limitations
- Routing rules (when each model is used)

### 3.2 Vision Models
- Supported image analysis tasks
- Current integration status

### 3.3 Math / Code Models
- Symbolic reasoning
- Code execution (if applicable)
- Planned improvements

---

## 4. System Behaviors

### 4.1 Reasoning Trace
- How RIS explains its decisions
- What is included (interpretation, assumptions, decision path)
- What is *not* included (raw chain-of-thought)

### 4.2 Error Handling
- Graceful fallback behavior
- Recovery strategies
- Logging and debugging hooks

### 4.3 Context Management
- How RIS maintains conversation state
- How it trims or summarizes context
- Memory boundaries

---

## 5. Current Limitations
- Known architectural gaps
- Performance bottlenecks
- Missing modules
- Areas of instability

---

## 6. Roadmap (Short-Term)
- Response Governor
- Model routing improvements
- Vision integration
- Self-introspection tools
- Automated testing harness

---

## 7. Roadmap (Long-Term)
- Full multi-model orchestration
- Persistent knowledge base
- Plugin/tool ecosystem
- Self-evaluation and benchmarking
