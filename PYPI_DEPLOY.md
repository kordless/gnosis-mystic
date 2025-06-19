# PyPI Build and Deploy Guide for Gnosis Mystic

## Prerequisites

1. **Install build tools**:
   ```bash
   pip install --upgrade pip
   pip install build twine
   ```

2. **PyPI Account Setup**:
   - Create account at https://pypi.org
   - Create account at https://test.pypi.org (for testing)
   - Generate API tokens for both

3. **Configure PyPI credentials**:
   ```bash
   # Create ~/.pypirc file
   cat > ~/.pypirc << EOF
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-YOUR_API_TOKEN_HERE

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-YOUR_TEST_API_TOKEN_HERE
   EOF
   ```

## Pre-Build Checklist

1. **Update version** in `src/mystic/__init__.py`:
   ```python
   __version__ = "0.1.0"  # Update this
   ```

2. **Verify package name availability**:
   - Check https://pypi.org/project/gnosis-mystic/
   - If taken, consider alternatives like:
     - `gnosis-mystic-ai`
     - `mystic-gnosis`
     - `gnosis-function-mystic`

3. **Update pyproject.toml** if needed:
   ```toml
   [project]
   name = "gnosis-mystic"  # Change if name is taken
   # ... rest of config
   ```

## Build Process

1. **Navigate to project root**:
   ```bash
   cd C:\Users\kord\Code\gnosis\gnosis-mystic
   ```

2. **Clean previous builds**:
   ```bash
   rm -rf dist/ build/ *.egg-info/
   ```

3. **Build the package**:
   ```bash
   python -m build
   ```

   This creates:
   - `dist/gnosis_mystic-0.1.0.tar.gz` (source distribution)
   - `dist/gnosis_mystic-0.1.0-py3-none-any.whl` (wheel)

4. **Verify build contents**:
   ```bash
   tar -tzf dist/gnosis_mystic-0.1.0.tar.gz
   ```

## Testing Before Publishing

1. **Test install locally**:
   ```bash
   pip install dist/gnosis_mystic-0.1.0-py3-none-any.whl
   python -c "import mystic; print(mystic.__version__)"
   ```

2. **Upload to Test PyPI first**:
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

3. **Test install from Test PyPI**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ gnosis-mystic
   ```

## Publishing to PyPI

1. **Final upload to PyPI**:
   ```bash
   python -m twine upload dist/*
   ```

2. **Verify installation**:
   ```bash
   pip install gnosis-mystic
   ```

## Complete Build Script

Create `build_and_deploy.py`:

```python
#!/usr/bin/env python3
"""
Build and deploy script for Gnosis Mystic
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success/failure"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {cmd}")
        print(f"Error: {e.stderr}")
        return False

def main():
    project_root = Path(__file__).parent
    
    print("🔨 Building Gnosis Mystic for PyPI...")
    
    # Clean previous builds
    print("\n1. Cleaning previous builds...")
    run_command("rm -rf dist/ build/ *.egg-info/", cwd=project_root)
    
    # Build package
    print("\n2. Building package...")
    if not run_command("python -m build", cwd=project_root):
        sys.exit(1)
    
    # Check package
    print("\n3. Checking package...")
    if not run_command("python -m twine check dist/*", cwd=project_root):
        print("Warning: Package check failed")
    
    # Test local install
    print("\n4. Testing local install...")
    if not run_command("pip install dist/*.whl --force-reinstall", cwd=project_root):
        print("Warning: Local install failed")
    
    print("\n✅ Build complete!")
    print("Next steps:")
    print("1. Test: python -m twine upload --repository testpypi dist/*")
    print("2. Deploy: python -m twine upload dist/*")

if __name__ == "__main__":
    main()
```

## Troubleshooting

### Common Issues:

1. **Package name already exists**:
   - Change name in `pyproject.toml`
   - Update imports if needed

2. **Missing dependencies**:
   - Check all imports work
   - Verify `requirements.txt` is complete

3. **Version conflicts**:
   - Increment version number
   - Clear build cache

4. **Upload failures**:
   - Check API token permissions
   - Verify network connectivity
   - Try uploading one file at a time

### Manual Upload Commands:

```bash
# Upload source distribution only
python -m twine upload dist/*.tar.gz

# Upload wheel only  
python -m twine upload dist/*.whl

# Upload with verbose output
python -m twine upload --verbose dist/*
```

## Post-Deploy

1. **Update documentation** with installation instructions
2. **Create GitHub release** with version tag
3. **Test installation** on clean environment:
   ```bash
   pip install gnosis-mystic
   python -c "import mystic; print('Success!')"
   ```

## Automation Options

For future releases, consider:
- GitHub Actions for automated builds
- Automated version bumping
- Changelog generation
- Release notes automation

---

**Ready to deploy!** 🚀
