"""
Getting Started with Gnosis Mystic

A quick start guide for users new to Gnosis Mystic.

TODO: Complete documentation according to IMPLEMENTATION_OUTLINE.md
"""

# Getting Started with Gnosis Mystic 🔮

## What is Gnosis Mystic?

Gnosis Mystic is an advanced Python function debugging system that lets you:
- **Hijack any function** to cache, mock, block, or redirect calls
- **Monitor functions in real-time** with performance tracking
- **Integrate with AI assistants** like Claude Desktop and Cursor
- **Debug interactively** with a professional REPL interface

## Quick Installation

```bash
# Install from PyPI (when released)
pip install gnosis-mystic

# Or install from source
git clone https://github.com/gnosis/gnosis-mystic.git
cd gnosis-mystic
pip install -e .
```

## 5-Minute Quick Start

### 1. Basic Function Hijacking

```python
import mystic

# Cache expensive function calls
@mystic.hijack(mystic.CacheStrategy(duration="1h"))
def expensive_api_call(data):
    # This will only execute once per hour for the same input
    return make_expensive_request(data)

# Mock function in development
@mystic.hijack(mystic.MockStrategy({"result": "test_data"}))
def external_service_call():
    # Returns mock data instead of calling real service
    return call_external_service()
```

### 2. Interactive Debugging

```bash
# Start the REPL
mystic repl

# In the REPL:
mystic> list hijacked
mystic> describe func expensive_api_call
mystic> watch expensive_api_call --real-time
```

### 3. AI Assistant Integration

```bash
# Setup Claude Desktop integration
mystic integrate --type=claude --auto

# Start MCP server for Claude
mystic server --transport=stdio
```

## Next Steps

- Read the [User Guide](user_guide/basic_usage.md) for detailed usage
- Check out [Examples](examples/) for real-world use cases
- Learn about [AI Integration](user_guide/ai_integration.md)

---

*Note: Gnosis Mystic is currently in development. See PROJECT_PLAN.md for roadmap.*