# Claude Code Implementation Prompt for Gnosis Mystic

## 🎯 **Project Overview**

You are tasked with implementing **Gnosis Mystic**, an advanced Python function debugging system with MCP (Model Context Protocol) integration for AI assistants. This is a professional-grade project that will revolutionize Python debugging by providing total function control, real-time monitoring, and seamless AI assistant integration.

## 📁 **Project Location & Structure**

**Base Directory**: `C:\Users\kord\Code\gnosis\gnosis-mystic`

The complete project structure has been created with comprehensive planning documents. Key files to reference:

- **`PROJECT_PLAN.md`** - Complete 10-week roadmap and feature specifications
- **`IMPLEMENTATION_OUTLINE.md`** - Detailed implementation requirements for every file
- **`PROJECT_STATUS.md`** - Current status and immediate next steps
- **`CONTRIBUTING.md`** - Development guidelines and coding standards

## 🚀 **Implementation Phase 1: Core Functionality (Priority)**

### **Primary Objectives**
Implement the core function hijacking, logging, and introspection system based on enhanced versions of the tools from `C:\Users\kord\Code\gnosis\gnosis-evolve`.

### **Files to Implement (Priority Order)**

#### 1. **Enhanced Function Hijacker** (`src/mystic/core/function_hijacker.py`)
**Base Reference**: `C:\Users\kord\Code\gnosis\gnosis-evolve\function_hijacker.py`

**Requirements**:
- Enhance the existing hijacker with MCP awareness
- Support multiple hijacking strategies (Cache, Mock, Block, Redirect, Analysis, Conditional)
- Add strategy chaining and prioritization
- Implement thread-safe hijacking registry
- Add performance metrics collection during hijacking
- Include MCP notification system for real-time updates
- Support context-aware hijacking (dev/test/prod environments)
- Preserve function signatures and metadata

**Key Classes to Implement**:
```python
class CallHijacker:
    # Enhanced version with MCP integration
    
class HijackStrategy:
    # Base strategy class
    
class CacheStrategy(HijackStrategy):
    # Disk-based caching with TTL
    
class MockStrategy(HijackStrategy):
    # Environment-aware mocking
    
class BlockStrategy(HijackStrategy):
    # Security-aware blocking
    
class RedirectStrategy(HijackStrategy):
    # Function redirection
    
class AnalysisStrategy(HijackStrategy):
    # Performance analysis
    
class ConditionalStrategy(HijackStrategy):
    # Conditional hijacking based on arguments/context

def hijack_function(*strategies, **kwargs):
    # Main decorator with multiple strategy support
```

#### 2. **Enhanced Function Logger** (`src/mystic/core/function_logger.py`)
**Base Reference**: `C:\Users\kord\Code\gnosis\gnosis-evolve\function_logger.py`

**Requirements**:
- Enhance existing logger with JSON-RPC support like mcp-debug
- Add MCP-style request/response logging with correlation IDs
- Support multiple output formats (console, file, JSON-RPC, structured)
- Implement sensitive data filtering and redaction
- Add real-time log streaming to MCP clients
- Include performance impact measurement
- Support configurable log levels and filtering

**Key Features**:
```python
class FunctionLogger:
    def log_mcp_request(self, method, params, request_id):
        # JSON-RPC style logging like mcp-debug
    
    def log_mcp_response(self, method, result, request_id):
        # Correlated response logging
    
    def format_for_transport(self, message, transport):
        # Transport-specific formatting

# Convenience decorators
@log_calls_and_returns()
@log_calls_only()  
@log_returns_only()
@detailed_log(max_length=500)
@filtered_log(arg_filter=..., return_filter=...)
```

#### 3. **Function Inspector** (`src/mystic/core/function_inspector.py`)
**Requirements**:
- Deep function introspection and analysis
- Extract function signatures, docstrings, type hints
- Generate JSON schemas for function arguments (for MCP tools)
- Analyze function dependencies and call graphs
- Detect function changes and modifications
- Extract performance characteristics
- Code complexity analysis

**Key Classes**:
```python
class FunctionInspector:
    def inspect_function(self, func) -> Dict[str, Any]:
        # Comprehensive function analysis
    
    def get_function_schema(self, func) -> Dict[str, Any]:
        # JSON schema for MCP tool registration
    
    def analyze_dependencies(self, func) -> List[str]:
        # Function dependency analysis
```

#### 4. **Performance Tracker** (`src/mystic/core/performance_tracker.py`)
**Requirements**:
- Real-time performance monitoring with <1% overhead
- Execution time tracking with statistical analysis
- Memory usage monitoring
- CPU usage tracking
- Call frequency and pattern analysis
- Performance baseline establishment
- Anomaly detection algorithms

#### 5. **State Manager** (`src/mystic/core/state_manager.py`)
**Requirements**:
- Function state management and persistence
- Cross-session state persistence
- State change notifications
- Conflict resolution for concurrent modifications
- State snapshots and rollback capabilities

#### 6. **Configuration System** (`src/mystic/config.py`)
**Requirements**:
- Complete the configuration management system
- Support file-based configuration loading/saving
- Environment variable integration
- Validation and type checking
- Configuration migration support

### **Testing Requirements**

#### **Unit Tests** (`tests/unit/test_core/`)
Create comprehensive unit tests for:
- `test_hijacker.py` - All hijacking strategies and combinations
- `test_logger.py` - All logging modes and formats
- `test_inspector.py` - Function analysis and schema generation
- `test_performance.py` - Performance tracking accuracy
- `test_config.py` - Configuration loading/saving

**Test Coverage Target**: >90%
**Performance Target**: <1% overhead for hijacked functions

### **Code Quality Standards**

#### **Style Guidelines**
- Follow PEP 8 with 100-character line limit
- Use type hints for all functions
- Include comprehensive docstrings (Google style)
- Use Black for formatting, Ruff for linting
- Include example usage in docstrings

#### **Error Handling**
- Graceful error handling with informative messages
- Proper exception hierarchies
- Logging of all errors and warnings
- Recovery mechanisms where possible

#### **Performance**
- Minimal overhead for hijacked functions (<1%)
- Efficient caching and storage mechanisms
- Asynchronous operations where beneficial
- Memory-conscious implementations

## 🔧 **Development Workflow**

### **Setup Commands**
```bash
cd C:\Users\kord\Code\gnosis\gnosis-mystic
make setup              # Setup development environment
make dev-install        # Install in development mode
```

### **Quality Checks**
```bash
make format             # Format code with Black/Ruff
make lint               # Run linting checks
make test               # Run all tests
make test-cov           # Run tests with coverage
make quick-check        # Format + lint + quick tests
```

## 📚 **Reference Materials**

### **Existing Code to Build Upon**
- **Function Hijacker**: `C:\Users\kord\Code\gnosis\gnosis-evolve\function_hijacker.py`
- **Function Logger**: `C:\Users\kord\Code\gnosis\gnosis-evolve\function_logger.py`
- **MCP Debug Reference**: `C:\Users\kord\Code\gnosis\development\mcp-debug\` (Go implementation for inspiration)

### **Key Documentation**
- **Architecture**: See `IMPLEMENTATION_OUTLINE.md` for detailed specs
- **Examples**: Check existing tools in gnosis-evolve for patterns
- **MCP Protocol**: Reference mcp-debug for JSON-RPC formatting

## 🎯 **Success Criteria**

### **Functional Requirements**
- [ ] Function hijacking works with all strategy types
- [ ] Multiple strategies can be chained effectively
- [ ] Logging captures all calls/returns with proper correlation
- [ ] Function inspection generates valid JSON schemas
- [ ] Performance tracking shows accurate metrics
- [ ] All unit tests pass with >90% coverage

### **Performance Requirements**
- [ ] <1% overhead for hijacked functions
- [ ] <100ms for function inspection operations
- [ ] <10MB memory footprint for typical usage
- [ ] Efficient caching with configurable TTL

### **Integration Requirements**
- [ ] CLI commands work for basic operations
- [ ] Configuration system loads/saves properly
- [ ] Logging integrates with Python's logging module
- [ ] Ready for MCP integration in Phase 2

## 🚨 **Important Notes**

### **Dependencies**
All required dependencies are listed in `requirements.txt`. The project uses:
- Click for CLI
- Rich for colored output
- Pydantic for data validation
- pytest for testing
- And others as specified

### **Compatibility**
- Target Python 3.8+ compatibility
- Cross-platform support (Windows, macOS, Linux)
- Thread-safe implementations
- Async-aware where beneficial

### **Security Considerations**
- Safe evaluation of user inputs
- Secure storage of sensitive data
- Access control for dangerous operations
- Audit logging for security events

## 🎬 **Implementation Strategy**

### **Phase 1A: Core Hijacking (Week 1)**
1. Implement enhanced `CallHijacker` class
2. Create all hijacking strategy classes
3. Build the main `hijack_function` decorator
4. Add comprehensive unit tests

### **Phase 1B: Logging & Inspection (Week 2)**
1. Implement enhanced `FunctionLogger` class
2. Create `FunctionInspector` with schema generation
3. Build `PerformanceTracker` and `StateManager`
4. Complete configuration system
5. Finalize test suite and documentation

## 🔮 **Vision**

You are building the foundation for the most advanced Python debugging system ever created. This will enable developers to:
- Have total control over any Python function
- Monitor function behavior in real-time
- Integrate seamlessly with AI assistants like Claude
- Debug interactively with professional tools

**The code you write will transform how Python developers debug their applications. Make it exceptional!** 🚀

---

**Ready to revolutionize Python debugging? Let's build something amazing!** ✨