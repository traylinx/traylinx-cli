# Contributing to Traylinx CLI Cortex

> Natural language interface for Traylinx CLI

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/traylinx/traylinx-cli.git
cd traylinx-cli

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest tests/cortex/ -v

# Run with coverage
pytest tests/cortex/ --cov=traylinx/cortex --cov-report=html

# Run specific test file
pytest tests/cortex/test_classifier.py -v
```

## Architecture Overview

```
traylinx/cortex/
├── intent/              # Intent classification
│   ├── classifier.py    # Two-tier classification (pattern + LLM)
│   ├── patterns.py      # Pattern matching rules
│   ├── extractors.py    # Parameter extraction
│   └── cache.py         # Intent caching
├── conversation/        # Multi-turn conversation
│   ├── state.py         # Conversation state machine
│   ├── resolver.py      # Reference resolution
│   └── clarifier.py     # Clarification generator
├── tools/               # Tool calling
│   ├── definitions.py   # OpenAI-style tool schemas
│   └── executor.py      # Tool execution pipeline
├── executor/            # Command execution
│   ├── executor.py      # CLI command executor
│   └── async_executor.py# Async execution
├── session/             # Session management
│   ├── manager.py       # Session lifecycle
│   ├── storage.py       # SQLite storage
│   ├── lazy.py          # Lazy loading
│   └── export.py        # History export
├── chat/                # Chat interface
│   ├── interface.py     # Typer CLI
│   └── repl.py          # Interactive REPL
├── switchai/            # LLM integration
│   └── client.py        # SwitchAILocal client
├── suggestions.py       # Workflow suggestions
├── chain.py             # Command chaining
├── errors.py            # Error handling
├── hot_reload.py        # Config hot-reload
├── config.py            # Configuration
├── types.py             # Type definitions
└── workspace.py         # Workspace bootstrap
```

## Key Concepts

### Intent Classification

Cortex uses a two-tier classification approach:

1. **Pattern Matching (Reflex)** - Fast, deterministic regex-based matching
2. **LLM Classification (Reasoning)** - Semantic understanding via SwitchAILocal

```python
from traylinx.cortex.intent.classifier import IntentClassifier

classifier = IntentClassifier()
intent = classifier.classify("start my agent")
# intent.command = "run", intent.confidence = 0.9
```

### Conversation State

Multi-turn conversations use a state machine:

```
IDLE → CLASSIFYING → EXECUTING → RESPONDING
                  ↘ CLARIFYING ↗
                       ↓
                     ERROR
```

### Tool Calling

CLI commands are defined as OpenAI-style tools:

```python
from traylinx.cortex.tools import TOOL_DEFINITIONS, ToolExecutor

executor = ToolExecutor()
result = executor.execute(tool_call)
```

## Adding New Commands

1. Add pattern to `intent/patterns.py`
2. Add tool definition to `tools/definitions.py`
3. Add handler to `executor/executor.py`
4. Add tests to `tests/cortex/`

## Code Style

- Use type hints for all public APIs
- Follow PEP 8, enforced by ruff
- Use dataclasses for data structures
- Prefer composition over inheritance

## Testing Guidelines

- Test all public APIs
- Mock external dependencies (SwitchAI, file system)
- Use pytest fixtures for common setup
- Aim for >85% coverage on new code

## Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Run `pytest tests/cortex/` locally
4. Submit PR with clear description
5. Address review feedback
