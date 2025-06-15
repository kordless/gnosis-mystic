#!/usr/bin/env python3
"""
Gnosis Mystic CLI Entry Point

Main command-line interface for the Mystic debugging system.
"""

from pathlib import Path
from typing import Optional

import click

from .config import MysticConfig, load_config
from .core import __version__


@click.group()
@click.version_option(version=__version__, prog_name="mystic")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: bool, debug: bool):
    """
    🔮 Gnosis Mystic - Advanced Python Function Debugging with MCP Integration

    Transform your Python debugging experience with AI-powered introspection.
    """
    # Ensure object exists for subcommands
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        ctx.obj["config"] = load_config(config)
    else:
        ctx.obj["config"] = MysticConfig()

    # Set global options
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug

    if debug:
        import logging

        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.option("--with-claude", is_flag=True, help="Setup Claude Desktop integration")
@click.option("--with-cursor", is_flag=True, help="Setup Cursor IDE integration")
@click.option(
    "--project-dir",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project directory to initialize",
)
@click.pass_context
def init(ctx: click.Context, with_claude: bool, with_cursor: bool, project_dir: Path):
    """Initialize Mystic in a project directory."""
    click.echo("🔮 Initializing Gnosis Mystic...")

    # TODO: Implement initialization logic
    click.echo(f"   📁 Project directory: {project_dir}")

    if with_claude:
        click.echo("   🧠 Setting up Claude Desktop integration...")
        # TODO: Generate Claude config

    if with_cursor:
        click.echo("   ⚡ Setting up Cursor IDE integration...")
        # TODO: Generate Cursor config

    click.echo("✅ Initialization complete!")


@cli.command()
@click.option("--endpoint", default="http://localhost:8090/mcp", help="MCP server endpoint")
@click.option("--auto-discover", is_flag=True, help="Auto-discover functions in current project")
@click.pass_context
def repl(ctx: click.Context, endpoint: str, auto_discover: bool):
    """Start the interactive REPL debugging interface."""
    click.echo("🔮 Starting Mystic REPL...")

    if auto_discover:
        click.echo("🔍 Auto-discovering functions...")

    # TODO: Import and start REPL
    # from .repl import InteractiveShell
    # shell = InteractiveShell(config=ctx.obj['config'])
    # shell.run()

    click.echo("💬 REPL interface not yet implemented")
    click.echo("   This will be available in Phase 3 of development")


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http", "sse"]),
    default="stdio",
    help="Transport protocol for MCP server",
)
@click.option("--host", default="localhost", help="Host to bind to (for http/sse transports)")
@click.option("--port", default=8899, help="Port to bind to (for http/sse transports)")
@click.option("--auto-discover", is_flag=True, help="Auto-discover and expose functions")
@click.pass_context
def server(ctx: click.Context, transport: str, host: str, port: int, auto_discover: bool):
    """Start the MCP server for AI assistant integration."""
    click.echo("🔮 Starting Mystic MCP Server...")
    click.echo(f"   📡 Transport: {transport}")

    if transport != "stdio":
        click.echo(f"   🌐 Binding to: {host}:{port}")

    if auto_discover:
        click.echo("🔍 Auto-discovering functions...")

    # TODO: Import and start MCP server
    # from .mcp import MCPServer
    # server = MCPServer(
    #     transport=transport,
    #     host=host,
    #     port=port,
    #     config=ctx.obj['config']
    # )
    # server.run()

    click.echo("🌐 MCP server not yet implemented")
    click.echo("   This will be available in Phase 2 of development")


@cli.command()
@click.argument("function_name")
@click.option(
    "--strategy",
    type=click.Choice(["cache", "mock", "block", "redirect", "analyze"]),
    default="analyze",
    help="Hijacking strategy to apply",
)
@click.option("--duration", help="Cache duration (e.g., '1h', '30m', '24h')")
@click.option("--mock-value", help="Mock return value (JSON)")
@click.pass_context
def hijack(ctx: click.Context, function_name: str, strategy: str, duration: str, mock_value: str):
    """Hijack a function with the specified strategy."""
    click.echo(f"🎯 Hijacking function: {function_name}")
    click.echo(f"   📋 Strategy: {strategy}")

    if strategy == "cache" and duration:
        click.echo(f"   ⏱️  Duration: {duration}")
    elif strategy == "mock" and mock_value:
        click.echo(f"   🎭 Mock value: {mock_value}")

    # TODO: Implement function hijacking
    click.echo("🔧 Function hijacking not yet implemented")
    click.echo("   This will be available in Phase 1 of development")


@cli.command()
@click.argument("function_name", required=False)
@click.option("--all", "show_all", is_flag=True, help="Show all hijacked functions")
@click.pass_context
def status(ctx: click.Context, function_name: Optional[str], show_all: bool):
    """Show status of hijacked functions."""
    if function_name:
        click.echo(f"📊 Status for function: {function_name}")
    elif show_all:
        click.echo("📊 Status of all hijacked functions:")
    else:
        click.echo("📊 Mystic system status:")

    # TODO: Implement status display
    click.echo("📈 Status display not yet implemented")


@cli.command()
@click.option(
    "--type",
    "integration_type",
    type=click.Choice(["claude", "cursor", "vscode"]),
    required=True,
    help="Type of integration to setup",
)
@click.option("--auto", is_flag=True, help="Automatic setup with defaults")
@click.pass_context
def integrate(ctx: click.Context, integration_type: str, auto: bool):
    """Setup AI assistant integrations."""
    click.echo(f"🤖 Setting up {integration_type} integration...")

    if auto:
        click.echo("   🔧 Using automatic configuration...")
    else:
        click.echo("   ⚙️  Using interactive configuration...")

    # TODO: Implement integration setup
    click.echo("🔌 Integration setup not yet implemented")
    click.echo("   This will be available in Phase 4 of development")


@cli.command()
@click.pass_context
def version(ctx: click.Context):
    """Show version information."""
    click.echo(f"🔮 Gnosis Mystic v{__version__}")
    click.echo("   Advanced Python Function Debugging with MCP Integration")
    click.echo("   https://github.com/gnosis/gnosis-mystic")


if __name__ == "__main__":
    cli()
