# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Java-Code-Reviewer-Agent is a LangGraph-based automated code review system that reviews Java Pull Requests against Alibaba Java development standards (华山版/泰山版). It supports GitHub and GitLab, with two modes:
- **audit_only**: Generates a Markdown report of issues sorted by severity
- **autofix**: Generates fixes and pushes a new branch to the PR

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run a single test
pytest tests/test_diff_parser.py -v
```

## Architecture

### LangGraph Pipeline

The review flow is a state machine in `src/java_code_reviewer/main.py` with 7 nodes:

```
input_node → crawler_node → context_retriever_node → reviewer_node → option_router → report_node/patch_node
```

1. **input_node**: Validates PR URL (GitHub/GitLab), checks scope whitelist
2. **crawler_node**: Fetches PR metadata and diff via `agents/github_agent.py` or `agents/gitlab_agent.py`
3. **context_retriever_node**: RAG-based retrieval of relevant Alibaba standards from FAISS vector store
4. **reviewer_node**: LLM (GPT-4o) reviews code against Alibaba standards, outputs issues as JSON
5. **option_router**: Routes to report_node (audit_only) or patch_node (autofix)
6. **report_node**: Generates Markdown table report sorted by severity
7. **patch_node**: Creates fix branch, applies patches, pushes via `git_ops/git_manager.py`

### State Management

`state/review_state.py` defines:
- `ReviewState` TypedDict: Contains all pipeline state
- `ReviewMode` Enum: `AUDIT_ONLY` or `AUTOFIX`
- `Severity` Enum: `BLOCKER` > `CRITICAL` > `WARNING` > `INFO`
- `Issue` TypedDict: severity, rule_id, file_path, line_number, message, code_snippet, suggestion

### RAG System

- `rag/alibaba_standards.py`: 20+ coding rules (Naming, Exception, Concurrency, Collection, SQL, OOP)
- `rag/knowledge_base.py`: FAISS vector store with OpenAI embeddings
- `rag/retriever.py`: Extracts Java symbols from diffs, performs similarity search

### LLM Integration

`llm/client.py` supports OpenAI (default) and Anthropic providers via LangChain. Configure via environment variables:
- `LLM_PROVIDER`: "openai" or "anthropic"
- `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`

### Configuration

`config.yaml` controls: GitHub/GitLab tokens, LLM settings, review limits (max_files: 50), git operations (clone_depth: 1, branch_prefix: "java-reviewer/"), RAG settings (embedding_model: text-embedding-3-small, top_k: 5)

## Entry Point

```python
from java_code_reviewer.main import run_review

result = run_review("https://github.com/org/repo/pull/123", mode="audit_only")
# or
result = run_review("https://github.com/org/repo/pull/123", mode="autofix")
```
