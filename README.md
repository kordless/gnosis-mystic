# Gnosis Mystic 🔮

**AI-Powered Python Function Analysis and Control**

Gnosis Mystic gives AI assistants direct access to your Python functions through runtime hijacking and intelligent analysis. Add minimal decorators, and Claude can inspect, optimize, and control your code in real-time.

## Inspiration and Work
Mystic was inspired by [Giantswarm's](https://giantswarm.io) [mcp-debug](https://github.com/giantswarm/mcp-debug).

Code by fairly stock Claude Code. Prompts, code sketches, and planning by Claude Desktop using Gnosis Evolve tools.

## ✨ Why Gnosis Mystic?

### The Problem
AI assistants are blind to your running code:
- They can't see function performance in real-time
- No direct access to runtime behavior and state
- Can't dynamically test optimizations
- Limited to static code analysis
- No way to experiment with function modifications safely

### The Solution
Gnosis Mystic creates a **direct AI-to-code interface**:
- **AI sees everything**: Real-time function calls, performance, and behavior
- **Safe experimentation**: Test caching, mocking, and optimizations instantly
- **Runtime control**: AI can modify function behavior without code changes
- **Intelligent analysis**: AI discovers bottlenecks and suggests improvements
- **Live debugging**: AI can inspect function state during execution

## 🚀 Core Capabilities

### 1. AI-Visible Function Monitoring
```python
@hijack_function(AnalysisStrategy())
def fetch_user_data(user_id):
    response = requests.get(f"https://api.example.com/users/{user_id}")
    return response.json()

# Claude can now see:
# - Call frequency and patterns
# - Performance metrics
# - Parameter distributions
# - Error rates and types
```

### 2. AI-Controlled Optimization
```python
# You add minimal decoration
@hijack_function()
def expensive_calculation(data):
    # Your logic unchanged
    return complex_math(data)

# Claude can experiment with:
# - Adding caching strategies
# - Performance profiling
# - Mock data for testing
# - Alternative implementations
```

### 3. Intelligent Security Analysis
```python
@hijack_function(SecurityStrategy())
def process_payment(user_id, credit_card, amount):
    # Your business logic unchanged
    return payment_processor.charge(credit_card, amount)

# Claude automatically detects and reports:
# - Sensitive data in logs
# - Security vulnerabilities
# - Data flow patterns
```

### 4. Dynamic Behavior Control
- **Runtime Strategies**: AI can apply caching, mocking, blocking without restarts
- **A/B Testing**: Compare function implementations in real-time
- **Environment Adaptation**: Different behaviors for dev/test/prod
- **Performance Experiments**: Test optimizations safely

## 🔧 Quick Start

```bash
# Install from source
git clone https://github.com/gnosis/gnosis-mystic.git
cd gnosis-mystic
pip install -e ".[web]"

# Initialize your project
cd /path/to/your/project
mystic init

# Start the server for AI integration
mystic serve

# Let Claude discover your functions
mystic discover
```

## 🎯 Example Usage

### Basic AI Integration
```python
import mystic

# Minimal decoration for AI visibility
@mystic.hijack()
def api_call(endpoint, data):
    return requests.post(f"https://api.com/{endpoint}", json=data)

# Claude can now:
# - See all calls and responses
# - Measure performance
# - Suggest optimizations
# - Test improvements
```

### Advanced Analysis
```python
@mystic.hijack(
    strategies=[
        mystic.AnalysisStrategy(track_performance=True),
        mystic.SecurityStrategy(scan_sensitive_data=True)
    ]
)
def process_user_data(user_info):
    # Your code unchanged
    return database.save(user_info)
```

## 💡 Real-World AI Integration

### Claude Desktop Setup
1. Initialize your project:
   ```bash
   cd /your/project
   mystic init
   ```

2. Start the server:
   ```bash
   mystic serve
   ```

3. Add to Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "gnosis-mystic": {
         "command": "python",
         "args": [
           "C:\\path\\to\\gnosis-mystic\\mystic_mcp_standalone.py",
           "--project-root", 
           "C:\\your\\project"
         ]
       }
     }
   }
   ```

4. AI-Powered Development:
   - **"Find my slowest functions"** - Claude analyzes performance data
   - **"Add caching to expensive calls"** - Claude applies optimizations
   - **"Check for security issues"** - Claude scans for vulnerabilities
   - **"Show me error patterns"** - Claude analyzes failure modes
   - **"Optimize this function"** - Claude experiments with improvements

## 🧠 AI Assistant Capabilities

Once integrated, Claude can:

### Function Discovery & Analysis
- Automatically find all decorated functions
- Analyze call patterns and performance
- Identify bottlenecks and optimization opportunities
- Generate performance reports

### Real-Time Optimization
- Apply caching strategies dynamically
- Test different implementations
- A/B test performance improvements
- Rollback changes instantly

### Security & Debugging
- Detect sensitive data exposure
- Track function call flows
- Identify error patterns
- Debug production issues safely

### Code Intelligence
- Suggest function improvements
- Recommend architectural changes
- Predict performance impacts
- Generate optimization plans

## 📊 Current Status

### ✅ What's Working Now
- **Function Hijacking**: Runtime interception with multiple strategies
- **AI Integration**: Claude can discover and control functions via MCP
- **Performance Tracking**: Real-time metrics with minimal overhead
- **Security Analysis**: Automatic sensitive data detection
- **CLI Tools**: Function discovery and server management

### 🚧 Coming Soon
- Enhanced AI analysis capabilities
- Web dashboard for monitoring
- IDE extensions for VS Code/Cursor
- Distributed debugging support

## 🏗️ How It Works

Gnosis Mystic creates a bridge between your code and AI:

1. **Minimal Decoration**: Add simple decorators to functions you want monitored
2. **Runtime Interception**: Captures all function calls and behavior
3. **AI Communication**: Streams data to AI assistants via MCP protocol
4. **Dynamic Control**: AI can modify function behavior in real-time
5. **Safe Experimentation**: Test changes without affecting core logic

```
Your Function + @hijack_function → Mystic Layer → AI Analysis
     ↑                                              ↓
     └────── Core Logic Preserved ←──── AI Control ──┘
```

## 🎯 Use Cases

### Development & Debugging
- **Performance Profiling**: AI identifies slow functions automatically
- **Error Analysis**: AI patterns in failures and suggests fixes
- **Code Quality**: AI reviews function behavior and suggests improvements

### Production Monitoring
- **Real-time Optimization**: AI applies performance improvements live
- **Security Monitoring**: AI detects suspicious patterns or data leaks
- **Capacity Planning**: AI predicts scaling needs from usage patterns

### Testing & QA
- **Intelligent Mocking**: AI creates realistic test data
- **Behavior Verification**: AI ensures functions work as expected
- **Regression Detection**: AI spots when function behavior changes

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) for details.

## 🔗 Related Projects

- **gnosis-evolve**: Original function hijacking foundation
- **mcp-debug**: MCP debugging reference implementation (inspiration)
- **Claude Desktop**: Primary AI assistant integration target

---

**The future of Python development: Your code, enhanced by AI.** 🔮✨

*Imagine Claude knowing exactly how your functions behave, optimizing them in real-time, and debugging issues before you even notice them. That's Gnosis Mystic.*