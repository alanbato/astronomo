def main() -> None:
    """Entry point for the Astronomo application."""
    from astronomo.astronomo import Astronomo

    app = Astronomo()
    app.run()
