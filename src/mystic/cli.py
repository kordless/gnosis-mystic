"""
Gnosis Mystic CLI - Main entry point for the mystic command

This provides the main CLI interface for running Gnosis Mystic from any directory.
"""

import os
import sys
import json
import click
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .config import Config
from .core.function_inspector import FunctionInspector


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Gnosis Mystic - Advanced Python Function Debugging with MCP Integration"""
    pass


@cli.command()
@click.option('--name', default=None, help='Project name (defaults to directory name)')
@click.option('--python', default=sys.executable, help='Python interpreter to use')
def init(name: Optional[str], python: str):
    """Initialize Gnosis Mystic in the current project"""
    current_dir = Path.cwd()
    project_name = name or current_dir.name
    
    click.echo(f"🔮 Initializing Gnosis Mystic for project: {project_name}")
    
    # Create .mystic directory
    mystic_dir = current_dir / ".mystic"
    mystic_dir.mkdir(exist_ok=True)
    
    # Create config file
    config_file = mystic_dir / "config.json"
    config = {
        "project_name": project_name,
        "project_root": str(current_dir),
        "python_interpreter": python,
        "ignore_patterns": [
            "*.pyc",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "env",
            ".pytest_cache",
            ".mypy_cache"
        ],
        "auto_discover": True,
        "mcp_enabled": True
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Create .gitignore for .mystic directory
    gitignore = mystic_dir / ".gitignore"
    gitignore.write_text("cache/\nlogs/\n*.log\n")
    
    # Create MCP config for Claude Desktop
    mcp_config = {
        "mcpServers": {
            f"gnosis-mystic-{project_name}": {
                "command": "python",
                "args": [
                    "-m",
                    "mystic.mcp_client",
                    "--project-root",
                    str(current_dir)
                ],
                "env": {
                    "PYTHONPATH": str(current_dir)
                }
            }
        }
    }
    
    mcp_config_file = mystic_dir / "claude_desktop_config.json"
    with open(mcp_config_file, 'w') as f:
        json.dump(mcp_config, f, indent=2)
    
    click.echo(f"✅ Created .mystic/config.json")
    click.echo(f"✅ Created .mystic/claude_desktop_config.json")
    click.echo()
    click.echo("📋 Next steps:")
    click.echo(f"1. Add the MCP config to Claude Desktop from: {mcp_config_file}")
    click.echo("2. Run 'mystic serve' to start the debugging server")
    click.echo("3. Run 'mystic discover' to see available functions")


@cli.command()
@click.option('--host', default='localhost', help='Server host')
@click.option('--port', default=8899, type=int, help='Server port')
@click.option('--reload', is_flag=True, help='Auto-reload on code changes')
def serve(host: str, port: int, reload: bool):
    """Start the Gnosis Mystic debugging server in the current directory"""
    current_dir = Path.cwd()
    
    # Add current directory to Python path
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # Set environment variable for the server
    os.environ['MYSTIC_PROJECT_ROOT'] = str(current_dir)
    
    click.echo(f"🔮 Starting Gnosis Mystic server for: {current_dir}")
    click.echo(f"📡 Server: http://{host}:{port}")
    click.echo(f"📚 API Docs: http://{host}:{port}/docs")
    click.echo(f"🏥 Health: http://{host}:{port}/health")
    click.echo()
    click.echo("Press Ctrl+C to stop the server")
    
    # Import and run the server
    from .mcp.server import run_server
    
    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")


@cli.command()
@click.option('--module', '-m', help='Specific module to discover')
@click.option('--pattern', '-p', default='*.py', help='File pattern to search')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def discover(module: Optional[str], pattern: str, output_json: bool):
    """Discover available functions in the current project"""
    current_dir = Path.cwd()
    
    # Add current directory to Python path
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    click.echo(f"🔍 Discovering functions in: {current_dir}")
    
    inspector = FunctionInspector()
    discovered_functions = []
    
    # Find Python files
    py_files = list(current_dir.rglob(pattern))
    
    # Filter out common directories to ignore
    ignore_dirs = {'.venv', 'venv', 'env', '.git', '__pycache__', '.pytest_cache'}
    py_files = [f for f in py_files if not any(ignore in f.parts for ignore in ignore_dirs)]
    
    for py_file in py_files:
        try:
            # Convert file path to module path
            relative_path = py_file.relative_to(current_dir)
            module_parts = relative_path.with_suffix('').parts
            module_name = '.'.join(module_parts)
            
            # Skip if module filter is specified and doesn't match
            if module and not module_name.startswith(module):
                continue
            
            # Try to import the module
            try:
                imported_module = __import__(module_name, fromlist=[''])
            except ImportError:
                continue
            
            # Inspect all functions in the module
            import inspect
            for name, obj in inspect.getmembers(imported_module, inspect.isfunction):
                if obj.__module__ == module_name:  # Only functions defined in this module
                    func_info = {
                        'module': module_name,
                        'name': name,
                        'full_name': f"{module_name}.{name}",
                        'file': str(py_file),
                        'line': inspect.getsourcelines(obj)[1]
                    }
                    
                    # Get additional info
                    try:
                        info = inspector.inspect_function(obj)
                        func_info['signature'] = str(info.signature)
                        func_info['docstring'] = info.metadata.docstring
                    except:
                        func_info['signature'] = str(inspect.signature(obj))
                        func_info['docstring'] = inspect.getdoc(obj)
                    
                    discovered_functions.append(func_info)
                    
        except Exception as e:
            if not output_json:
                click.echo(f"⚠️  Error processing {py_file}: {e}", err=True)
    
    # Output results
    if output_json:
        click.echo(json.dumps(discovered_functions, indent=2))
    else:
        click.echo(f"\n📦 Found {len(discovered_functions)} functions:\n")
        
        for func in discovered_functions:
            click.echo(f"  📍 {func['full_name']}")
            click.echo(f"     📄 {func['file']}:{func['line']}")
            if func['docstring']:
                first_line = func['docstring'].split('\n')[0]
                click.echo(f"     📝 {first_line}")
            click.echo()


@cli.command()
@click.argument('function_name')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed information')
def inspect(function_name: str, detailed: bool):
    """Inspect a specific function"""
    current_dir = Path.cwd()
    
    # Add current directory to Python path
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    try:
        # Import the function
        parts = function_name.split('.')
        module_name = '.'.join(parts[:-1])
        func_name = parts[-1]
        
        module = __import__(module_name, fromlist=[func_name])
        func = getattr(module, func_name)
        
        # Inspect it
        inspector = FunctionInspector()
        info = inspector.inspect_function(func)
        
        click.echo(f"🔍 Function: {function_name}")
        
        # Format signature nicely
        params = []
        for p in info.signature.parameters:
            param_str = p['name']
            if p.get('annotation'):
                param_str += f": {p['annotation']}"
            if p.get('has_default'):
                param_str += f" = {p['default']}"
            params.append(param_str)
        
        sig_str = f"({', '.join(params)})"
        if info.signature.return_type:
            sig_str += f" -> {info.signature.return_type}"
        if info.signature.is_async:
            sig_str = f"async {sig_str}"
            
        click.echo(f"📝 Signature: {sig_str}")
        if info.metadata.source_file and info.metadata.source_lines:
            click.echo(f"📄 File: {info.metadata.source_file}:{info.metadata.source_lines[0]}")
        elif info.metadata.source_file:
            click.echo(f"📄 File: {info.metadata.source_file}")
        
        if info.metadata.docstring:
            click.echo(f"\n📖 Documentation:")
            click.echo(info.metadata.docstring)
        
        if detailed:
            click.echo(f"\n🔧 Details:")
            click.echo(f"  - Async: {info.metadata.is_async}")
            click.echo(f"  - Generator: {info.metadata.is_generator}")
            click.echo(f"  - Method: {info.metadata.is_method}")
            click.echo(f"  - Decorators: {', '.join(info.metadata.decorators) or 'None'}")
            
            if info.dependencies.imports:
                click.echo(f"\n📦 Dependencies:")
                for imp in info.dependencies.imports:
                    click.echo(f"  - {imp}")
            
            if info.analysis.calls_functions:
                click.echo(f"\n📞 Calls:")
                for call in info.analysis.calls_functions:
                    click.echo(f"  - {call}")
        
    except Exception as e:
        click.echo(f"❌ Error inspecting {function_name}: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Check Gnosis Mystic status in the current project"""
    current_dir = Path.cwd()
    mystic_dir = current_dir / ".mystic"
    
    if not mystic_dir.exists():
        click.echo("❌ Gnosis Mystic not initialized in this directory")
        click.echo("💡 Run 'mystic init' to initialize")
        sys.exit(1)
    
    # Load config
    config_file = mystic_dir / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        
        click.echo(f"🔮 Gnosis Mystic Status")
        click.echo(f"📁 Project: {config['project_name']}")
        click.echo(f"📍 Root: {config['project_root']}")
        click.echo(f"🐍 Python: {config['python_interpreter']}")
        
        # Check for cache
        cache_dir = mystic_dir / "cache"
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("*.cache"))
            click.echo(f"💾 Cache: {len(cache_files)} entries")
        
        # Check for logs
        log_dir = mystic_dir / "logs"
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            click.echo(f"📜 Logs: {len(log_files)} files")
    else:
        click.echo("⚠️  Config file missing")


if __name__ == '__main__':
    cli()