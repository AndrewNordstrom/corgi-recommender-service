# Build a CLI Tool in 5 Minutes

This guide shows you how to build a simple command-line interface (CLI) tool for Corgi using Python's `click` library. You'll create a tool that allows users to fetch recommendations, log interactions, and manage privacy settings from the terminal.

## Prerequisites

- Python 3.6+
- `click` library (`pip install click`)
- `requests` library (`pip install requests`)
- `rich` library for pretty output (`pip install rich`)
- A Corgi API key

## Project Setup

Create a new directory for your CLI tool and set up a basic structure:

```
corgi-cli/
├── corgi_cli.py
├── README.md
└── requirements.txt
```

Add the following to `requirements.txt`:

```
click>=8.0.0
requests>=2.25.0
rich>=10.0.0
```

## Basic CLI Implementation

Here's the complete implementation of a basic CLI tool:

```python
#!/usr/bin/env python3
"""
Corgi CLI - A command-line interface for the Corgi Recommender Service
"""

import os
import sys
import json
import click
import requests
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
import html
import re

# Initialize Rich console
console = Console()

class CorgiAPI:
    """Client for the Corgi Recommender Service API."""
    
    def __init__(self, api_key, base_url="https://api.corgi-recs.io"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_recommendations(self, user_id, limit=10, exclude_seen=True, 
                           languages=None, debug=False):
        """Get personalized recommendations for a user."""
        params = {
            "user_id": user_id,
            "limit": limit,
            "exclude_seen": "true" if exclude_seen else "false",
            "debug": "true" if debug else "false"
        }
        
        if languages:
            params["languages"] = languages
        
        response = requests.get(
            f"{self.base_url}/api/v1/recommendations",
            headers=self.headers,
            params=params
        )
        
        response.raise_for_status()
        return response.json()
    
    def log_interaction(self, user_id, post_id, action_type, context=None):
        """Log a user interaction with a post."""
        data = {
            "user_alias": user_id,
            "post_id": post_id,
            "action_type": action_type
        }
        
        if context:
            data["context"] = context
            
        response = requests.post(
            f"{self.base_url}/api/v1/interactions",
            headers=self.headers,
            json=data
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_privacy_settings(self, user_id):
        """Get privacy settings for a user."""
        response = requests.get(
            f"{self.base_url}/api/v1/privacy",
            headers=self.headers,
            params={"user_id": user_id}
        )
        
        response.raise_for_status()
        return response.json()
    
    def update_privacy_settings(self, user_id, tracking_level):
        """Update privacy settings for a user."""
        data = {
            "user_id": user_id,
            "tracking_level": tracking_level
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/privacy",
            headers=self.headers,
            json=data
        )
        
        response.raise_for_status()
        return response.json()

def strip_html(text):
    """Remove HTML tags from text."""
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()

def format_timestamp(timestamp):
    """Format ISO timestamp to a readable format."""
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d %H:%M:%S')

@click.group()
@click.option('--api-key', envvar='CORGI_API_KEY', help='Corgi API key (or set CORGI_API_KEY env var)')
@click.option('--base-url', default='https://api.corgi-recs.io', help='API base URL')
@click.pass_context
def cli(ctx, api_key, base_url):
    """Corgi Recommender Service CLI"""
    if not api_key:
        console.print("[bold red]Error:[/] API key is required. Set --api-key or CORGI_API_KEY environment variable.")
        sys.exit(1)
    
    ctx.ensure_object(dict)
    ctx.obj['api'] = CorgiAPI(api_key=api_key, base_url=base_url)

@cli.command()
@click.option('--user-id', required=True, help='User ID to get recommendations for')
@click.option('--limit', default=5, type=int, help='Number of recommendations to return')
@click.option('--languages', help='Comma-separated list of language codes (e.g., "en,es")')
@click.option('--no-exclude-seen', is_flag=True, help='Include posts the user has already seen')
@click.option('--debug', is_flag=True, help='Include debug information in output')
@click.option('--json', 'json_output', is_flag=True, help='Output raw JSON')
@click.pass_context
def recommendations(ctx, user_id, limit, languages, no_exclude_seen, debug, json_output):
    """Get personalized recommendations for a user"""
    api = ctx.obj['api']
    
    try:
        result = api.get_recommendations(
            user_id=user_id,
            limit=limit,
            exclude_seen=not no_exclude_seen,
            languages=languages,
            debug=debug
        )
        
        if json_output:
            # Raw JSON output
            console.print(json.dumps(result, indent=2))
            return
            
        # Pretty display
        posts = result['recommendations']
        
        console.print(f"\n[bold green]Found {len(posts)} recommendations for user {user_id}[/]")
        
        for i, post in enumerate(posts, 1):
            # Create a table for each post
            table = Table(show_header=False, box=None)
            table.add_column("Field", style="blue")
            table.add_column("Value")
            
            table.add_row("Author", f"[bold]{post['account']['display_name']}[/] (@{post['account']['username']})")
            table.add_row("Posted", format_timestamp(post['created_at']))
            table.add_row("Content", strip_html(post['content'])[:150] + ("..." if len(post['content']) > 150 else ""))
            table.add_row("Reason", f"[italic]{post['recommendation_reason']}[/]")
            table.add_row("Score", f"{post['ranking_score']:.2f}")
            table.add_row("Post ID", post['id'])
            
            console.print(Panel(table, title=f"[bold]Recommendation {i}/{len(posts)}[/]", expand=False))
        
        # If debug info was requested and available, show it
        if debug and 'debug_info' in result:
            debug_info = result['debug_info']
            
            debug_table = Table(show_header=False)
            debug_table.add_column("Metric", style="cyan")
            debug_table.add_column("Value")
            
            debug_table.add_row("User interactions", str(debug_info.get('user_interactions_count', 'N/A')))
            debug_table.add_row("Candidates evaluated", str(debug_info.get('candidates_evaluated', 'N/A')))
            
            weights = debug_info.get('factor_weights', {})
            weights_str = "\n".join([f"{k}: {v}" for k, v in weights.items()])
            debug_table.add_row("Factor weights", weights_str)
            
            console.print(Panel(debug_table, title="[bold]Debug Info[/]", expand=False))
            
    except requests.RequestException as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)

@cli.command()
@click.option('--user-id', required=True, help='User ID')
@click.option('--post-id', required=True, help='Post ID')
@click.option('--action', required=True, type=click.Choice(['favorite', 'bookmark', 'reblog', 'more_like_this', 'less_like_this']), help='Interaction type')
@click.option('--source', default='cli', help='Source of the interaction')
@click.pass_context
def interact(ctx, user_id, post_id, action, source):
    """Log a user interaction with a post"""
    api = ctx.obj['api']
    
    context = {
        "source": source,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        result = api.log_interaction(
            user_id=user_id,
            post_id=post_id,
            action_type=action,
            context=context
        )
        
        console.print(f"[bold green]Success![/] Logged {action} interaction for post {post_id}")
        console.print(f"Interaction ID: {result.get('interaction_id', 'N/A')}")
        
    except requests.RequestException as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)

@cli.command()
@click.option('--user-id', required=True, help='User ID to get privacy settings for')
@click.pass_context
def privacy(ctx, user_id):
    """Get privacy settings for a user"""
    api = ctx.obj['api']
    
    try:
        result = api.get_privacy_settings(user_id)
        
        table = Table(show_header=False)
        table.add_column("Setting", style="blue")
        table.add_column("Value")
        
        table.add_row("User ID", result.get('user_id', 'N/A'))
        table.add_row("Tracking Level", f"[bold]{result.get('tracking_level', 'N/A')}[/]")
        
        if 'created_at' in result:
            table.add_row("Created At", format_timestamp(result['created_at']))
            
        if 'updated_at' in result:
            table.add_row("Updated At", format_timestamp(result['updated_at']))
        
        console.print(Panel(table, title="[bold]Privacy Settings[/]", expand=False))
        
    except requests.RequestException as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)

@cli.command()
@click.option('--user-id', required=True, help='User ID to update privacy settings for')
@click.option('--level', required=True, type=click.Choice(['full', 'limited', 'none']), help='Tracking level')
@click.pass_context
def set_privacy(ctx, user_id, level):
    """Update privacy settings for a user"""
    api = ctx.obj['api']
    
    try:
        result = api.update_privacy_settings(user_id, level)
        
        console.print(f"[bold green]Success![/] Updated privacy settings for user {user_id}")
        console.print(f"Tracking level set to: [bold]{result.get('tracking_level', 'N/A')}[/]")
        
    except requests.RequestException as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)

@cli.command()
@click.option('--user-id', required=True, help='User ID')
@click.option('--interactive', '-i', is_flag=True, help='Enter interactive mode')
@click.pass_context
def explore(ctx, user_id, interactive):
    """Explore recommendations interactively"""
    api = ctx.obj['api']
    
    if not interactive:
        # Just get and display recommendations
        ctx.invoke(recommendations, user_id=user_id, limit=5)
        return
    
    try:
        while True:
            console.print("\n[bold cyan]Corgi Recommendation Explorer[/]")
            console.print("1. Get recommendations")
            console.print("2. View privacy settings")
            console.print("3. Update privacy settings")
            console.print("4. Quit")
            
            choice = console.input("\nEnter choice (1-4): ")
            
            if choice == '1':
                limit = int(console.input("Number of recommendations (1-20) [5]: ") or "5")
                languages = console.input("Languages (comma-separated, e.g., en,es) []: ")
                debug = console.input("Include debug info? (y/n) [n]: ").lower() == 'y'
                
                result = api.get_recommendations(
                    user_id=user_id,
                    limit=limit,
                    languages=languages or None,
                    debug=debug
                )
                
                posts = result['recommendations']
                console.print(f"\n[bold green]Found {len(posts)} recommendations[/]")
                
                for i, post in enumerate(posts):
                    # Display post
                    md = f"""
                    ## {i+1}/{len(posts)}: {post['account']['display_name']} (@{post['account']['username']})
                    
                    {strip_html(post['content'])}
                    
                    [Posted: {format_timestamp(post['created_at'])}]
                    
                    **Reason:** {post['recommendation_reason']}
                    **Score:** {post['ranking_score']:.2f}
                    """
                    
                    console.print(Markdown(md))
                    
                    # Interaction menu
                    console.print("[bold cyan]Actions:[/] (f)avorite, (b)ookmark, (r)eblog, (m)ore like this, (l)ess like this, (n)ext, (q)uit")
                    action = console.input("Action: ").lower()
                    
                    if action == 'q':
                        return
                    elif action == 'n':
                        continue
                    elif action in ['f', 'favorite']:
                        api.log_interaction(user_id, post['id'], 'favorite', {"source": "cli_explorer"})
                        console.print("[green]✓[/] Marked as favorite")
                    elif action in ['b', 'bookmark']:
                        api.log_interaction(user_id, post['id'], 'bookmark', {"source": "cli_explorer"})
                        console.print("[green]✓[/] Bookmarked")
                    elif action in ['r', 'reblog']:
                        api.log_interaction(user_id, post['id'], 'reblog', {"source": "cli_explorer"})
                        console.print("[green]✓[/] Reblogged")
                    elif action in ['m', 'more']:
                        api.log_interaction(user_id, post['id'], 'more_like_this', {"source": "cli_explorer"})
                        console.print("[green]✓[/] Noted: more like this")
                    elif action in ['l', 'less']:
                        api.log_interaction(user_id, post['id'], 'less_like_this', {"source": "cli_explorer"})
                        console.print("[green]✓[/] Noted: less like this")
                
                # Show debug info if requested
                if debug and 'debug_info' in result:
                    debug_info = result['debug_info']
                    console.print("\n[bold cyan]Debug Info:[/]")
                    console.print(f"User interactions: {debug_info.get('user_interactions_count', 'N/A')}")
                    console.print(f"Candidates evaluated: {debug_info.get('candidates_evaluated', 'N/A')}")
                    console.print("Factor weights:")
                    for k, v in debug_info.get('factor_weights', {}).items():
                        console.print(f"  {k}: {v}")
            
            elif choice == '2':
                # View privacy settings
                ctx.invoke(privacy, user_id=user_id)
            
            elif choice == '3':
                # Update privacy settings
                console.print("\n[bold cyan]Privacy Levels:[/]")
                console.print("full - Maximum personalization (stores all interactions)")
                console.print("limited - Balanced approach (stores aggregate data only)")
                console.print("none - Maximum privacy (no personalization)")
                
                level = console.input("\nEnter new tracking level: ")
                if level in ['full', 'limited', 'none']:
                    result = api.update_privacy_settings(user_id, level)
                    console.print(f"[bold green]Success![/] Privacy level set to: {result['tracking_level']}")
                else:
                    console.print("[bold red]Error:[/] Invalid privacy level")
            
            elif choice == '4':
                return
            
            else:
                console.print("[bold yellow]Invalid choice. Please enter 1-4.[/]")
    
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Exiting interactive mode[/]")
    except requests.RequestException as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)

if __name__ == '__main__':
    cli(obj={})
```

## Usage Examples

Make the script executable:

```bash
chmod +x corgi_cli.py
```

### Getting Recommendations

```bash
# Set your API key as an environment variable
export CORGI_API_KEY=your_api_key_here

# Get recommendations
./corgi_cli.py recommendations --user-id user_12345 --limit 3

# Get recommendations in specific languages
./corgi_cli.py recommendations --user-id user_12345 --languages en,es

# Get recommendations with debug info
./corgi_cli.py recommendations --user-id user_12345 --debug

# Output raw JSON
./corgi_cli.py recommendations --user-id user_12345 --json
```

### Logging Interactions

```bash
# Log a favorite interaction
./corgi_cli.py interact --user-id user_12345 --post-id post_67890 --action favorite

# Log with a custom source
./corgi_cli.py interact --user-id user_12345 --post-id post_67890 --action bookmark --source "mobile_app"
```

### Managing Privacy Settings

```bash
# Get current privacy settings
./corgi_cli.py privacy --user-id user_12345

# Update privacy settings
./corgi_cli.py set-privacy --user-id user_12345 --level limited
```

### Interactive Mode

The interactive mode allows you to explore recommendations and interact with them:

```bash
./corgi_cli.py explore --user-id user_12345 --interactive
```

## Packaging Your CLI

To make your CLI tool easily installable, create a `setup.py` file:

```python
from setuptools import setup

setup(
    name="corgi-cli",
    version="0.1.0",
    py_modules=["corgi_cli"],
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "rich>=10.0.0",
    ],
    entry_points="""
        [console_scripts]
        corgi=corgi_cli:cli
    """,
)
```

Then install it:

```bash
pip install -e .
```

Now you can use it as a global command:

```bash
corgi recommendations --user-id user_12345
```

## Advanced Improvements

Here are some ways to enhance your CLI tool:

### Configuration File

Add support for a configuration file to store API keys and default settings:

```python
import configparser
import os

def load_config():
    config = configparser.ConfigParser()
    config_file = os.path.expanduser('~/.corgi.ini')
    
    if os.path.exists(config_file):
        config.read(config_file)
        
    return config

def save_config(config):
    config_file = os.path.expanduser('~/.corgi.ini')
    
    with open(config_file, 'w') as f:
        config.write(f)

@cli.command()
@click.option('--api-key', help='Corgi API key')
@click.option('--base-url', help='API base URL')
@click.option('--default-user', help='Default user ID')
def configure(api_key, base_url, default_user):
    """Configure CLI settings"""
    config = load_config()
    
    if 'corgi' not in config:
        config['corgi'] = {}
        
    if api_key:
        config['corgi']['api_key'] = api_key
        
    if base_url:
        config['corgi']['base_url'] = base_url
        
    if default_user:
        config['corgi']['default_user'] = default_user
        
    save_config(config)
    console.print("[bold green]Configuration saved![/]")
```

### Shell Completion

Add shell completion support:

```python
@cli.command()
@click.option('--shell', type=click.Choice(['bash', 'zsh', 'fish']), default='bash')
def completion(shell):
    """Generate shell completion script"""
    from click.shell_completion import get_completion_class
    
    comp_cls = get_completion_class(shell)
    comp = comp_cls(cli, "corgi", "_CORGI_COMPLETE")
    
    script = comp.source()
    console.print(script)
    console.print(f"\n[bold cyan]To enable completion, add this to your {shell} configuration file:[/]")
    
    if shell == 'bash':
        console.print("eval \"$(corgi completion --shell bash)\"")
    elif shell == 'zsh':
        console.print("eval \"$(corgi completion --shell zsh)\"")
    elif shell == 'fish':
        console.print("corgi completion --shell fish | source")
```

### Output Formatting

Add support for different output formats:

```python
@cli.command()
@click.option('--user-id', required=True, help='User ID')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), default='table')
@click.pass_context
def interactions(ctx, user_id, format):
    """Get user interactions"""
    api = ctx.obj['api']
    
    try:
        # Get user interactions
        response = requests.get(
            f"{api.base_url}/api/v1/interactions/user/{user_id}",
            headers=api.headers
        )
        
        response.raise_for_status()
        result = response.json()
        
        interactions = result.get('interactions', [])
        
        if format == 'json':
            # Output JSON
            console.print(json.dumps(interactions, indent=2))
            
        elif format == 'csv':
            # Output CSV
            import csv
            from io import StringIO
            
            output = StringIO()
            if interactions:
                fieldnames = ['id', 'post_id', 'action_type', 'created_at']
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(interactions)
                
                console.print(output.getvalue())
            else:
                console.print("No interactions found")
                
        else:
            # Output table
            if interactions:
                table = Table(show_header=True)
                table.add_column("ID", style="cyan")
                table.add_column("Post ID")
                table.add_column("Action")
                table.add_column("Created At")
                
                for interaction in interactions:
                    table.add_row(
                        interaction.get('id', 'N/A'),
                        interaction.get('post_id', 'N/A'),
                        interaction.get('action_type', 'N/A'),
                        format_timestamp(interaction.get('created_at', ''))
                    )
                
                console.print(table)
            else:
                console.print("No interactions found")
        
    except requests.RequestException as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)
```

## Next Steps

- Explore the [Python Client Example](python.md) for more integration ideas
- Learn about [Elk integration](elk.md) for a web client
- Check out the [API Reference](../api/overview.md) for more endpoints to integrate