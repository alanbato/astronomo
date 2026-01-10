# Installation

Astronomo requires Python 3.10 or later.

## Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. Install Astronomo as a tool:

```bash
uv tool install astronomo
```

Or add it to an existing project:

```bash
uv add astronomo
```

## Using pip

Install from PyPI:

```bash
pip install astronomo
```

## From Source

Clone the repository and install with uv:

```bash
git clone https://github.com/alanbato/astronomo.git
cd astronomo
uv sync
```

Run the development version:

```bash
uv run astronomo
```

## Verifying Installation

After installation, verify that Astronomo is working:

```bash
astronomo --version
```

You should see the version number printed. Then launch the browser:

```bash
astronomo
```

This opens Astronomo with the default home page. Press ++ctrl+q++ to quit.

## Optional Features

### Inline Image Display (Chafa)

Astronomo can display images (PNG, JPEG, GIF, WebP) as ANSI art directly in the terminal using [Chafa](https://hpjansson.org/chafa/). This feature is optional and requires the `chafa.py` package.

**Install with pip:**

```bash
pip install astronomo[chafa]
```

**Install with uv tool:**

```bash
uv tool install astronomo --with chafa.py
```

**From source (development):**

```bash
uv sync --group chafa
```

After installation, enable image display in Settings (++ctrl+comma++) → Appearance → Show Images.

## Next Steps

- [Quick Start](quickstart.md) - Learn the basics of browsing with Astronomo
- [Configuration](reference/configuration.md) - Customize your setup
