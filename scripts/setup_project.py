# Quick Start Script for Gnosis Mystic Development

import os
import sys
from pathlib import Path

def create_directory_structure():
    """Create the complete directory structure for Gnosis Mystic."""
    
    base_dir = Path("C:/Users/kord/Code/gnosis/gnosis-mystic")
    
    # Directory structure to create
    directories = [
        # Source directories
        "src/mystic/core",
        "src/mystic/mcp", 
        "src/mystic/repl",
        "src/mystic/monitoring",
        "src/mystic/integrations",
        "src/mystic/ui",
        "src/mystic/storage",
        "src/mystic/security",
        "src/mystic/utils",
        
        # Test directories
        "tests/unit/test_core",
        "tests/unit/test_mcp",
        "tests/unit/test_repl",
        "tests/unit/test_integrations",
        "tests/integration",
        "tests/fixtures",
        "tests/benchmarks",
        
        # Documentation directories
        "docs/user_guide",
        "docs/developer_guide", 
        "docs/api_reference",
        "docs/examples",
        
        # Tools directories
        "tools/build_tools",
        "tools/dev_scripts",
        "tools/deployment",
        
        # Config directories
        "config/themes",
        "config/profiles",
        "config/integrations",
        "config/security",
        
        # Data directories
        "data/cache",
        "data/metrics",
        "data/logs",
        "data/backups",
        "data/snapshots",
        
        # Scripts directory
        "scripts",
        
        # Web interface (future)
        "web/static/css",
        "web/static/js",
        "web/static/images",
        "web/templates"
    ]
    
    # Create all directories
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Create __init__.py files for Python packages
    python_packages = [
        "src/mystic",
        "src/mystic/core",
        "src/mystic/mcp",
        "src/mystic/repl", 
        "src/mystic/monitoring",
        "src/mystic/integrations",
        "src/mystic/ui",
        "src/mystic/storage",
        "src/mystic/security",
        "src/mystic/utils",
        "tests",
        "tests/unit",
        "tests/unit/test_core",
        "tests/unit/test_mcp",
        "tests/unit/test_repl",
        "tests/unit/test_integrations",
        "tests/integration",
        "tests/fixtures",
        "tests/benchmarks"
    ]
    
    for package in python_packages:
        init_file = base_dir / package / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Gnosis Mystic package."""\n')
            print(f"📦 Created: {package}/__init__.py")

if __name__ == "__main__":
    print("🔮 Creating Gnosis Mystic directory structure...")
    create_directory_structure()
    print("✨ Directory structure created successfully!")
    print("\n📋 Next steps:")
    print("   1. Review PROJECT_PLAN.md for overall roadmap")
    print("   2. Review IMPLEMENTATION_OUTLINE.md for detailed implementation plan")
    print("   3. Start with Phase 1: Core functionality")
    print("   4. Install dependencies: pip install -r requirements.txt")
    print("   5. Run tests: pytest tests/")
