import typer
from typing import Optional

cli = typer.Typer(
    name="astronomo",
    help="A Gemini browser for the terminal",
    add_completion=False,
)


@cli.command()
def run(
    url: Optional[str] = typer.Argument(
        None,
        help="Gemini URL to open on startup (e.g., gemini://geminiprotocol.net/)",
    ),
) -> None:
    """Launch Astronomo, optionally opening a Gemini URL."""
    from astronomo.astronomo import Astronomo

    astronomo_app = Astronomo(initial_url=url)
    astronomo_app.run()


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
