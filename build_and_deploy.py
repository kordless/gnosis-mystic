#!/usr/bin/env python3
"""
Build and deploy script for Gnosis Mystic
"""
import subprocess
import sys
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success/failure"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {cmd}")
        if result.stdout:
            print(f"  Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {cmd}")
        print(f"  Error: {e.stderr}")
        return False

def clean_build_dirs(project_root):
    """Clean build directories"""
    dirs_to_clean = ["dist", "build", "src/mystic.egg-info"]
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"✓ Removed {dir_path}")

def main():
    project_root = Path(__file__).parent
    
    print("🔨 Building Gnosis Mystic for PyPI...")
    print(f"📁 Project root: {project_root}")
    
    # Check if we're in the right directory
    if not (project_root / "pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Are you in the right directory?")
        sys.exit(1)
    
    # Clean previous builds
    print("\n1. Cleaning previous builds...")
    clean_build_dirs(project_root)
    
    # Install/upgrade build tools
    print("\n2. Installing build tools...")
    if not run_command("pip install --upgrade build twine"):
        print("❌ Failed to install build tools")
        sys.exit(1)
    
    # Build package
    print("\n3. Building package...")
    if not run_command("python -m build", cwd=project_root):
        print("❌ Build failed")
        sys.exit(1)
    
    # Check what was built
    dist_dir = project_root / "dist"
    if dist_dir.exists():
        files = list(dist_dir.glob("*"))
        print(f"\n📦 Built files:")
        for file in files:
            print(f"  - {file.name}")
    
    # Check package
    print("\n4. Checking package...")
    if not run_command("python -m twine check dist/*", cwd=project_root):
        print("⚠️  Warning: Package check failed")
    
    print("\n✅ Build complete!")
    print("\n📋 Next steps:")
    print("1. Test upload: python -m twine upload --repository testpypi dist/*")
    print("2. Production upload: python -m twine upload dist/*")
    print("3. Install test: pip install gnosis-mystic")
    
    # Show current version
    try:
        import sys
        sys.path.insert(0, str(project_root / "src"))
        import mystic
        print(f"\n📌 Current version: {mystic.__version__}")
    except ImportError:
        print("\n⚠️  Could not import mystic to check version")

if __name__ == "__main__":
    main()
