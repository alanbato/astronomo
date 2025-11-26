from pathlib import Path

import typer

from astronomo.astronomo_app import Astronomo

cli = typer.Typer(
    name="astronomo",
    help="A Gemini browser for the terminal",
    add_completion=False,
)


@cli.command()
def run(
    url: str | None = typer.Argument(
        None,
        help="Gemini URL to open on startup (e.g., gemini://geminiprotocol.net/)",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (default: ~/.config/astronomo/config.toml)",
    ),
) -> None:
    """Launch Astronomo, optionally opening a Gemini URL."""
    astronomo_app = Astronomo(initial_url=url, config_path=config)
    astronomo_app.run()


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
