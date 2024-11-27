import click
import json
import os
from pathlib import Path

CONFIG_FILE = Path("config.json")

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "voice": "alloy",
        "prompt": "You are a helpful AI assistant",
        "saved_prompts": {}
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

@click.group()
def cli():
    """AI Voice Calling Application CLI"""
    pass

@cli.command()
@click.option("--number", required=True, help="Phone number to call")
def call(number):
    """Initiate a call to the specified number"""
    config = load_config()
    click.echo(f"Initiating call to {number}")
    click.echo(f"Using voice: {config['voice']}")
    click.echo(f"Using prompt: {config['prompt'][:50]}...")
    # Call your main application logic here
    from main import initiate_call
    initiate_call(number, config)

@cli.group()
def config():
    """Manage application configuration"""
    pass

@config.command()
@click.option("--name", type=click.Choice(["alloy", "echo", "fable", "onyx", "nova"]), 
              help="Set the voice to use")
def voice(name):
    """Configure the AI voice settings"""
    config = load_config()
    if name:
        config["voice"] = name
        save_config(config)
        click.echo(f"Voice set to: {name}")
    else:
        click.echo(f"Current voice: {config['voice']}")

@config.command()
@click.option("--set", help="Set the current prompt")
@click.option("--save", nargs=2, help="Save a prompt with a name")
@click.option("--load", help="Load a saved prompt")
@click.option("--list", "list_prompts", is_flag=True, help="List saved prompts")
def prompt(set, save, load, list_prompts):
    """Configure the AI prompt/personality"""
    config = load_config()
    
    if set:
        config["prompt"] = set
        save_config(config)
        click.echo("Prompt updated successfully")
    
    elif save:
        name, prompt_text = save
        config["saved_prompts"][name] = prompt_text
        save_config(config)
        click.echo(f"Prompt saved as '{name}'")
    
    elif load:
        if load in config["saved_prompts"]:
            config["prompt"] = config["saved_prompts"][load]
            save_config(config)
            click.echo(f"Loaded prompt: '{load}'")
        else:
            click.echo(f"No prompt found with name: {load}")
    
    elif list_prompts:
        click.echo("Saved prompts:")
        for name, prompt_text in config["saved_prompts"].items():
            click.echo(f"\n{name}:")
            click.echo(f"{prompt_text[:100]}...")
    
    else:
        click.echo("Current prompt:")
        click.echo(config["prompt"])

@config.command()
def show():
    """Show current configuration"""
    config = load_config()
    click.echo("\nCurrent Configuration:")
    click.echo(f"Voice: {config['voice']}")
    click.echo("\nPrompt:")
    click.echo(config['prompt'])
    click.echo("\nSaved Prompts:")
    for name in config["saved_prompts"]:
        click.echo(f"- {name}")

@cli.command()
def voices():
    """List available voices"""
    click.echo("\nAvailable Voices:")
    click.echo("- alloy    (Neutral)")
    click.echo("- echo     (Male)")
    click.echo("- fable    (Female)")
    click.echo("- onyx     (Male)")
    click.echo("- nova     (Female)")

if __name__ == "__main__":
    cli()