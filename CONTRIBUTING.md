# Contributing to Gnosis Mystic

Thank you for your interest in contributing to Gnosis Mystic! This document provides guidelines and information for contributors.

## 🚀 Quick Start for Contributors

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/gnosis-mystic.git
   cd gnosis-mystic
   ```

2. **Set up Development Environment**
   ```bash
   make setup
   # or manually:
   python scripts/setup_project.py
   pip install -e ".[dev]"
   pre-commit install
   ```

3. **Run Tests**
   ```bash
   make test
   ```

## 📋 Development Workflow

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow the implementation guidelines in `IMPLEMENTATION_OUTLINE.md`
   - Write tests for new functionality
   - Update documentation as needed

3. **Run Quality Checks**
   ```bash
   make quick-check  # format, lint, and quick tests
   make all-checks   # comprehensive checks
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Use the provided PR template
   - Include tests and documentation
   - Reference any related issues

## 🎯 Implementation Priorities

See `PROJECT_PLAN.md` for the overall roadmap. Current priorities:

### Phase 1: Core Functionality (Active)
- Enhanced function hijacking (`src/mystic/core/function_hijacker.py`)
- Enhanced logging system (`src/mystic/core/function_logger.py`)
- Function introspection (`src/mystic/core/function_inspector.py`)
- Performance tracking (`src/mystic/core/performance_tracker.py`)

### Phase 2: MCP Integration (Next)
- MCP server implementation (`src/mystic/mcp/server.py`)
- JSON-RPC protocol handler (`src/mystic/mcp/protocol_handler.py`)
- Transport management (`src/mystic/mcp/transport_manager.py`)

## 📝 Code Style Guidelines

### Python Code Style
- Follow PEP 8
- Use Black for formatting (`make format`)
- Use Ruff for linting (`make lint`)
- Use type hints (checked with mypy)
- Maximum line length: 100 characters

### Documentation Style
- Use Google-style docstrings
- Include type information in docstrings
- Provide examples for complex functions
- Update relevant documentation files

### Commit Messages
Follow conventional commit format:
- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance tasks

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (slower, realistic)
├── benchmarks/     # Performance benchmarks
└── fixtures/       # Test data and helpers
```

### Writing Tests
- Write unit tests for all new functionality
- Include integration tests for complex features
- Use descriptive test names
- Test edge cases and error conditions
- Maintain >90% code coverage

### Running Tests
```bash
make test           # All tests
make quick-test     # Fast unit tests only
make test-cov       # Tests with coverage report
make benchmark      # Performance benchmarks
```

## 📚 Documentation Guidelines

### Types of Documentation
1. **Code Documentation**: Docstrings and comments
2. **User Documentation**: `docs/user_guide/`
3. **Developer Documentation**: `docs/developer_guide/`
4. **API Reference**: `docs/api_reference/`
5. **Examples**: `docs/examples/`

### Documentation Standards
- Keep documentation up-to-date with code changes
- Include practical examples
- Use clear, concise language
- Test all code examples

## 🎨 UI/UX Guidelines

### REPL Interface
- Use emoji indicators for status (🎯, 💾, 🎭, etc.)
- Provide colored output for better readability
- Include progress indicators for long operations
- Offer helpful error messages with suggestions

### Output Formatting
- Use consistent color schemes
- Provide multiple verbosity levels
- Support both human-readable and machine-readable output
- Include timing information for operations

## 🔒 Security Guidelines

### Code Security
- Never commit secrets or credentials
- Validate all user inputs
- Use secure defaults
- Follow principle of least privilege

### Function Hijacking Security
- Provide sandboxed execution options
- Implement access control for sensitive functions
- Audit all hijacking operations
- Warn users about potentially dangerous operations

## 🐛 Bug Reports

When reporting bugs:
1. Use the bug report template
2. Include steps to reproduce
3. Provide environment information
4. Include relevant logs and error messages
5. Suggest potential fixes if possible

## 💡 Feature Requests

When requesting features:
1. Use the feature request template
2. Explain the use case and motivation
3. Provide examples of expected behavior
4. Consider implementation complexity
5. Check if similar features exist

## 🏗️ Architecture Decisions

### Design Principles
- **Modularity**: Each component should have a single responsibility
- **Extensibility**: Easy to add new hijacking strategies and integrations
- **Performance**: Minimal overhead for hijacked functions
- **Security**: Safe by default with opt-in dangerous operations
- **Usability**: Intuitive interface for both beginners and experts

### Dependencies
- Prefer standard library when possible
- Choose mature, well-maintained dependencies
- Consider licensing compatibility
- Minimize dependency tree size

## 📊 Performance Guidelines

### Performance Targets
- <1% overhead for hijacked functions
- <100ms REPL command response time
- <50ms MCP protocol latency
- <10MB memory footprint for typical projects

### Performance Testing
- Include benchmarks for new features
- Test with realistic workloads
- Monitor memory usage
- Profile critical paths

## 🤝 Code Review Process

### For Reviewers
- Check code quality and style
- Verify test coverage
- Review documentation updates
- Test functionality manually
- Consider security implications

### For Contributors
- Respond to feedback promptly
- Make requested changes
- Keep PRs focused and atomic
- Update PR description as needed

## 📈 Release Process

### Version Numbering
Follow semantic versioning (SemVer):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version number bumped
- [ ] Release notes prepared

## 🙋‍♀️ Getting Help

### Questions and Discussions
- GitHub Discussions for general questions
- GitHub Issues for bug reports and feature requests
- Pull Request comments for code-specific questions

### Contact
- Project maintainers: See `pyproject.toml`
- Email: team@gnosis.dev (for sensitive issues)

## 📄 License

By contributing to Gnosis Mystic, you agree that your contributions will be licensed under the Apache 2.0 License.

---

**Thank you for contributing to Gnosis Mystic! Together we're building the future of Python function debugging.** 🔮✨