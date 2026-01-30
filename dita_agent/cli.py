#!/usr/bin/env python3
"""
DITA Migration Agent CLI

A single command-line tool that handles everything:
- Setup: Clones repos, installs Vale, configures API
- Run: Executes the migration workflow

Usage:
    dita-agent setup              # One-time setup
    dita-agent run                # Run migration on entire project
    dita-agent run --assembly x   # Run on specific assembly
    dita-agent run --topics a b   # Run on specific topics
"""

import json
import os
import shutil
import subprocess
import sys
import venv
from getpass import getpass
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from dita_agent import __version__

# Console for rich output
console = Console()

# Configuration
TOOL_NAME = "dita-agent"
TOOL_DIR = Path.home() / ".dita-agent"
CONFIG_FILE = TOOL_DIR / "config.json"
TOOLS_DIR = TOOL_DIR / "tools"
VENV_DIR = TOOL_DIR / "venv"

# Repositories to clone
REPOS = {
    "asciidoctor-dita-vale": "https://github.com/jhradilek/asciidoctor-dita-vale.git",
    "callouts-conversion": "https://github.com/gtrivedi88/callouts-conversion.git",
}

# Supported Gemini models
GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3-flash-preview",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]


# ============================================================================
# Utility Functions
# ============================================================================


def print_header(title: str):
    """Print a styled header."""
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))


def print_success(message: str):
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message."""
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str):
    """Print info message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict):
    """Save configuration to file."""
    TOOL_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


# ============================================================================
# Virtual Environment Management
# ============================================================================


def get_venv_python() -> Path:
    """Get the path to the Python executable in the virtual environment."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_venv_pip() -> Path:
    """Get the path to pip in the virtual environment."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def create_virtual_environment():
    """
    Create an isolated virtual environment for tool dependencies.
    
    This ensures that tool dependencies don't conflict with the user's
    existing Python packages.
    """
    print_info("Creating isolated virtual environment...")
    
    if VENV_DIR.exists():
        print_info("Virtual environment already exists, checking...")
        if get_venv_python().exists():
            print_success("Virtual environment is ready")
            return
        else:
            print_warning("Virtual environment corrupted, recreating...")
            shutil.rmtree(VENV_DIR)
    
    try:
        # Create venv with pip included
        venv.create(VENV_DIR, with_pip=True)
        print_success(f"Created virtual environment at {VENV_DIR}")
        
        # Upgrade pip in the venv
        subprocess.run(
            [str(get_venv_python()), "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            check=True,
        )
        print_success("Upgraded pip in virtual environment")
        
    except Exception as e:
        print_error(f"Failed to create virtual environment: {e}")
        raise click.Abort()


def install_tool_dependencies():
    """
    Install dependencies for cloned tools into the isolated venv.
    
    This keeps tool dependencies completely separate from the user's environment.
    """
    print_info("Installing tool dependencies into isolated environment...")
    
    pip_path = get_venv_pip()
    
    for name in REPOS.keys():
        repo_path = TOOLS_DIR / name
        requirements_file = repo_path / "requirements.txt"
        
        if requirements_file.exists():
            print_info(f"Installing dependencies for {name}...")
            try:
                subprocess.run(
                    [str(pip_path), "install", "-r", str(requirements_file)],
                    capture_output=True,
                    check=True,
                )
                print_success(f"Installed dependencies for {name}")
            except subprocess.CalledProcessError as e:
                print_warning(f"Could not install dependencies for {name}: {e.stderr.decode() if e.stderr else e}")


# ============================================================================
# Setup Command
# ============================================================================


def clone_repositories():
    """Clone required repositories to ~/.dita-agent/tools/."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    
    for name, url in REPOS.items():
        repo_path = TOOLS_DIR / name
        
        if repo_path.exists():
            print_info(f"{name} already exists, pulling latest...")
            try:
                subprocess.run(
                    ["git", "-C", str(repo_path), "pull"],
                    capture_output=True,
                    check=True,
                )
                print_success(f"Updated {name}")
            except subprocess.CalledProcessError as e:
                print_warning(f"Could not update {name}: {e}")
        else:
            print_info(f"Cloning {name}...")
            try:
                subprocess.run(
                    ["git", "clone", url, str(repo_path)],
                    capture_output=True,
                    check=True,
                )
                print_success(f"Cloned {name}")
            except subprocess.CalledProcessError as e:
                print_error(f"Failed to clone {name}: {e}")
                raise click.Abort()


def check_vale_installed() -> bool:
    """Check if Vale is installed."""
    return shutil.which("vale") is not None


def install_vale():
    """Install Vale linter."""
    print_info("Checking Vale installation...")

    if check_vale_installed():
        print_success("Vale is already installed")
        return

    print_warning("Vale not found. Please install Vale manually:")
    console.print("\n  [bold]macOS:[/bold]    brew install vale")
    console.print("  [bold]Linux:[/bold]    Download from https://vale.sh/docs/vale-cli/installation/")
    console.print("  [bold]Windows:[/bold]  choco install vale\n")

    if not click.confirm("Continue without Vale? (You'll need to install it before running)", default=False):
        raise click.Abort()


def sync_vale_styles():
    """Download and sync Vale style packages (RedHat, AsciiDoc) and copy AsciiDocDITA."""
    if not check_vale_installed():
        print_warning("Skipping Vale styles sync (Vale not installed)")
        return

    print_info("Syncing Vale style packages...")

    # Create unified styles directory
    styles_dir = TOOLS_DIR / "vale-styles"
    styles_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Download RedHat and AsciiDoc packages using Vale
    temp_config = TOOLS_DIR / ".vale-temp.ini"
    config_content = f"""StylesPath = {styles_dir}

Packages = RedHat, AsciiDoc

[*.adoc]
BasedOnStyles = RedHat, AsciiDoc, AsciiDocDITA
"""

    temp_config.write_text(config_content)

    try:
        # Run vale sync to download packages
        result = subprocess.run(
            ["vale", "--config", str(temp_config), "sync"],
            cwd=str(TOOLS_DIR),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print_success("Downloaded RedHat and AsciiDoc styles")
        else:
            print_warning(f"Could not sync Vale styles: {result.stderr}")
    except Exception as e:
        print_warning(f"Could not sync Vale styles: {e}")
    finally:
        # Clean up temp config
        if temp_config.exists():
            temp_config.unlink()

    # Step 2: Copy AsciiDocDITA styles from asciidoctor-dita-vale repo
    asciidoc_dita_source = TOOLS_DIR / "asciidoctor-dita-vale" / "styles" / "AsciiDocDITA"
    asciidoc_dita_dest = styles_dir / "AsciiDocDITA"

    if asciidoc_dita_source.exists():
        try:
            # Remove existing if present
            if asciidoc_dita_dest.exists():
                shutil.rmtree(asciidoc_dita_dest)

            # Copy the directory
            shutil.copytree(asciidoc_dita_source, asciidoc_dita_dest)
            print_success("Copied AsciiDocDITA styles")
        except Exception as e:
            print_warning(f"Could not copy AsciiDocDITA styles: {e}")
    else:
        print_warning("AsciiDocDITA styles not found in asciidoctor-dita-vale repo")


def configure_api() -> dict:
    """Configure LLM API settings."""
    config = {}
    
    console.print("\n[bold]LLM API Configuration[/bold]\n")
    
    # Provider (currently only Gemini)
    config["provider"] = "gemini"
    print_info("Using Gemini API (default provider)")
    
    # API endpoint
    default_url = "https://generativelanguage.googleapis.com"
    api_url = click.prompt(
        "API endpoint URL",
        default=default_url,
        show_default=True,
    )
    config["base_url"] = api_url
    
    # Model selection
    console.print("\n[bold]Available models:[/bold]")
    for i, model in enumerate(GEMINI_MODELS, 1):
        marker = "[green]→[/green]" if i == 1 else " "
        console.print(f"  {marker} {i}. {model}")
    
    model_choice = click.prompt(
        "\nSelect model (number)",
        default="1",
        type=click.IntRange(1, len(GEMINI_MODELS)),
    )
    config["model"] = GEMINI_MODELS[model_choice - 1]
    
    # API key
    console.print(f"\n[yellow]Your API key will be stored at {CONFIG_FILE}[/yellow]")
    api_key = getpass("Enter your Gemini API key: ")
    if not api_key:
        print_error("API key is required")
        raise click.Abort()
    config["api_key"] = api_key
    
    # Optional: Custom certificate
    cert_path = click.prompt(
        "Custom SSL certificate path (leave empty for default)",
        default="",
        show_default=False,
    )
    if cert_path:
        config["cert_path"] = cert_path
    
    return config


@click.command()
def setup():
    """
    One-time setup: Clone repos, create venv, install Vale, configure API.
    
    This command sets up everything needed to run the DITA Migration Agent:
    - Creates an isolated virtual environment at ~/.dita-agent/venv/
    - Clones required tool repositories to ~/.dita-agent/tools/
    - Installs tool dependencies into the isolated venv (not your system Python)
    - Checks/installs Vale linter
    - Configures Gemini API credentials
    - Creates configuration file at ~/.dita-agent/config.json
    """
    print_header("DITA Migration Agent - Setup")

    console.print(f"Version: [bold]{__version__}[/bold]\n")

    # Ensure base directory exists before creating subdirectories
    TOOL_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Create isolated virtual environment
    console.print("[bold]Step 1/4: Create Isolated Environment[/bold]")
    create_virtual_environment()
    
    # Step 2: Clone repositories
    console.print("\n[bold]Step 2/4: Clone Tool Repositories[/bold]")
    clone_repositories()
    
    # Step 3: Install tool dependencies into venv
    console.print("\n[bold]Step 3/4: Install Tool Dependencies[/bold]")
    install_tool_dependencies()
    
    # Step 4: Check Vale
    console.print("\n[bold]Step 4/4: Vale Linter[/bold]")
    install_vale()
    sync_vale_styles()

    # Step 5: Configure API
    console.print("\n[bold]Step 5/5: API Configuration[/bold]")
    config = configure_api()
    save_config(config)
    
    # Success message - explicitly show config locations
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]✓ Setup complete![/bold green]\n\n"
        f"[bold]Configuration stored at:[/bold] {CONFIG_FILE}\n"
        f"[bold]Tools installed at:[/bold] {TOOLS_DIR}\n"
        f"[bold]Isolated venv at:[/bold] {VENV_DIR}\n\n"
        "[dim]Tool dependencies are installed in an isolated environment\n"
        "and will not affect your system Python packages.[/dim]\n\n"
        "Next step: Navigate to your project and run:\n"
        "  [cyan]dita-agent run[/cyan]",
        border_style="green",
    ))


# ============================================================================
# Run Command  
# ============================================================================


def ensure_gitignore_updated(project_dir: Path):
    """
    Ensure .dita-agent/ is in .gitignore BEFORE creating any files.
    
    This prevents backup files from appearing in the user's git changes,
    which would be confusing (showing 1000s of "changed" files).
    """
    gitignore = project_dir / ".gitignore"
    entry = ".dita-agent/"
    
    if gitignore.exists():
        content = gitignore.read_text()
        if entry not in content:
            with open(gitignore, "a") as f:
                f.write(f"\n# DITA Migration Agent\n{entry}\n")
            print_info(f"Added {entry} to .gitignore")
    else:
        gitignore.write_text(f"# DITA Migration Agent\n{entry}\n")
        print_info(f"Created .gitignore with {entry}")


def validate_setup() -> dict:
    """Validate that setup has been completed and return config."""
    if not CONFIG_FILE.exists():
        print_error("Setup not completed. Please run: dita-agent setup")
        raise click.Abort()
    
    config = load_config()
    
    if not config.get("api_key"):
        print_error("API key not configured. Please run: dita-agent setup")
        raise click.Abort()
    
    if not check_vale_installed():
        print_error("Vale is not installed. Please install Vale and try again.")
        raise click.Abort()
    
    return config


@click.command()
@click.option(
    "--assembly", "-a",
    type=click.Path(exists=True, path_type=Path),
    help="Process a single assembly and all its includes",
)
@click.option(
    "--topics", "-t",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Process specific topic files (up to 10)",
)
@click.option(
    "--limit", "-l",
    type=int,
    default=None,
    help="Process first N files with issues",
)
@click.option(
    "--dry-run", "-n",
    is_flag=True,
    help="Preview changes without applying them",
)
def run(assembly: Optional[Path], topics: tuple, limit: Optional[int], dry_run: bool):
    """
    Run the DITA migration agent.
    
    Processes AsciiDoc files through three phases:
    
    1. Content Type Assignment - Add :_mod-docs-content-type: attribute
    2. Callouts Conversion - Convert callout markers to DITA format  
    3. DITA Issues - Fix all remaining Vale errors
    
    Examples:
    
        dita-agent run                           # Process entire project
        dita-agent run --assembly master.adoc    # Process one assembly
        dita-agent run --topics a.adoc b.adoc    # Process specific files
        dita-agent run --limit 5                 # Process first 5 files
        dita-agent run --dry-run                 # Preview only
    """
    print_header("DITA Migration Agent - Run")
    
    # Validate setup
    config = validate_setup()
    project_dir = Path.cwd()
    
    # CRITICAL: Update .gitignore FIRST before creating any files
    ensure_gitignore_updated(project_dir)
    
    # Validate options
    if assembly and topics:
        print_error("Cannot use --assembly and --topics together")
        raise click.Abort()
    
    if topics and len(topics) > 10:
        print_error("Maximum 10 topics allowed")
        raise click.Abort()
    
    # Display scope
    if assembly:
        print_info(f"Scope: Assembly [bold]{assembly}[/bold] + all includes")
    elif topics:
        print_info(f"Scope: {len(topics)} specific topic(s)")
    elif limit:
        print_info(f"Scope: First {limit} files with issues")
    else:
        print_info("Scope: Entire project")
    
    if dry_run:
        print_warning("DRY RUN MODE - No changes will be made")
    
    # Import and run the agent
    # TODO: Implement agent orchestrator in Chunk 10
    from dita_agent.agent import DITAAgent
    
    agent = DITAAgent(
        config=config,
        project_dir=project_dir,
        assembly=assembly,
        topics=list(topics) if topics else None,
        limit=limit,
        dry_run=dry_run,
    )
    
    success = agent.run()
    
    sys.exit(0 if success else 1)


# ============================================================================
# Status Command
# ============================================================================


@click.command()
def status():
    """Show current configuration and tool status."""
    print_header("DITA Migration Agent - Status")
    
    # Version
    console.print(f"Version: [bold]{__version__}[/bold]\n")
    
    # Configuration
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    if CONFIG_FILE.exists():
        config = load_config()
        table.add_row("Config file", str(CONFIG_FILE))
        table.add_row("Provider", config.get("provider", "Not set"))
        table.add_row("Model", config.get("model", "Not set"))
        table.add_row("API Key", "***configured***" if config.get("api_key") else "Not set")
        table.add_row("Base URL", config.get("base_url", "Not set"))
    else:
        table.add_row("Config file", "[red]Not found[/red]")
    
    console.print(table)
    
    # Virtual Environment
    console.print("\n[bold]Isolated Environment:[/bold]")
    venv_python = get_venv_python()
    if venv_python.exists():
        console.print(f"  Virtual env: [green]✓ Ready[/green]")
        console.print(f"  Python: {venv_python}")
    else:
        console.print(f"  Virtual env: [red]✗ Not created[/red]")
        console.print(f"  [dim]Run 'dita-agent setup' to create[/dim]")
    
    # Tools
    console.print("\n[bold]Tools:[/bold]")
    
    vale_status = "[green]✓ Installed[/green]" if check_vale_installed() else "[red]✗ Not installed[/red]"
    console.print(f"  Vale: {vale_status}")
    
    for name in REPOS.keys():
        repo_path = TOOLS_DIR / name
        repo_status = "[green]✓ Installed[/green]" if repo_path.exists() else "[red]✗ Not installed[/red]"
        console.print(f"  {name}: {repo_status}")
    
    # Directories
    console.print(f"\n[bold]Directories:[/bold]")
    console.print(f"  Tool directory: {TOOL_DIR}")
    console.print(f"  Isolated venv: {VENV_DIR}")
    console.print(f"  Config file: {CONFIG_FILE}")


# ============================================================================
# Main CLI Group
# ============================================================================


@click.group()
@click.version_option(version=__version__, prog_name=TOOL_NAME)
def main():
    """
    DITA Migration Agent - Fix AsciiDoc files for DITA compatibility.
    
    A command-line tool that automatically fixes AsciiDoc documentation
    to make it compatible with DITA (Darwin Information Typing Architecture).
    
    Quick Start:
    
        1. dita-agent setup     # One-time setup
        2. cd your-project
        3. dita-agent run       # Fix all issues
    """
    pass


# Register commands
main.add_command(setup)
main.add_command(run)
main.add_command(status)


if __name__ == "__main__":
    main()
