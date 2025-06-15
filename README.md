# Gnosis Mystic 🔮

**Advanced Python Function Debugging with MCP Integration**

Gnosis Mystic is a comprehensive Python function debugging and introspection system that combines function hijacking, logging, and real-time monitoring with MCP (Model Context Protocol) integration. It enables AI assistants like Claude to directly debug, monitor, and control Python functions in real-time.

## ✨ Key Features

- 🎭 **Advanced Function Hijacking**: Cache, mock, block, redirect, or analyze any function
- 📝 **Intelligent Logging**: MCP-aware JSON-RPC style logging with correlation
- 💬 **Interactive REPL**: Professional debugging shell with autocompletion
- 🤖 **AI Assistant Integration**: Native Claude Desktop and Cursor IDE support
- 👁️ **Real-time Monitoring**: Live function change detection and performance tracking
- 🛡️ **Security First**: Sandboxed execution and access control
- 🚀 **Zero Configuration**: Auto-discovery and intelligent defaults

## 🚀 Quick Start

```bash
# Install
pip install gnosis-mystic

# Quick setup with Claude integration
mystic init --with-claude

# Start interactive debugging
mystic repl

# Or start MCP server for AI assistants
mystic server --transport=stdio
```

## 🎯 Example Usage

### Function Hijacking
```python
import mystic

@mystic.hijack(
    strategies=[
        mystic.CacheStrategy(duration="1h"),
        mystic.MockStrategy(development=True),
        mystic.AnalysisStrategy(track_performance=True)
    ]
)
def expensive_api_call(data):
    return external_api.process(data)
```

### Interactive REPL
```bash
mystic> list hijacked
mystic> describe func expensive_api_call
mystic> hijack new_function cache --duration=30m
mystic> watch my_function --real-time
mystic> claude setup --auto
```

### AI Assistant Integration
Once set up, Claude can directly:
- Discover all your Python functions
- Execute functions with proper arguments
- Monitor function performance
- Suggest optimizations
- Debug issues in real-time

## 📋 Project Status

🚧 **In Development** - See [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed roadmap

**Current Phase**: Foundation (Core Infrastructure)
- ✅ Project structure established
- 🔄 Enhanced function hijacking (in progress)
- ⏳ MCP protocol integration (planned)
- ⏳ Interactive REPL (planned)
- ⏳ AI assistant integration (planned)

## 🏗️ Architecture

```
gnosis-mystic/
├── 🔧 src/mystic/core/          # Core function control
├── 🌐 src/mystic/mcp/           # MCP protocol integration  
├── 💬 src/mystic/repl/          # Interactive debugging
├── 👁️ src/mystic/monitoring/    # Real-time monitoring
├── 🤖 src/mystic/integrations/  # AI assistant integrations
├── 🎨 src/mystic/ui/            # User interface
├── 🛡️ src/mystic/security/      # Security features
└── 🧰 src/mystic/utils/         # Utilities
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) for details.

## 🔗 Related Projects

- **gnosis-evolve**: Original function hijacking tools
- **mcp-debug**: MCP debugging inspiration (Go)
- **Claude Desktop**: Primary AI assistant target

---

**Transform your Python debugging experience with AI-powered introspection.** 🔮✨