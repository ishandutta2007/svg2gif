# svg2gif 🎨➡️🎬

A high-performance CLI tool & Python library for converting animated SVG files into optimized, looping animated GIFs using headless Playwright and Pillow.

---

## ✨ Features

- **Headless Browser Rendering**: Accurate rendering of CSS animations, SMIL, and JavaScript-driven SVG animations using Playwright (Chromium).
- **Aspect Ratio Preservation**: Automatically detects SVG viewBox/dimensions to maintain precise aspect ratios during frame capture.
- **Smart Optimization Engine**:
  - **Downscaling**: Automatically resizes large SVGs to ideal max-width parameters for smaller file outputs.
  - **Palette Quantization**: Applies 256-color adaptive palette conversion per frame.
  - **Frame Compression**: Leverages Pillow's optimization to discard redundant frame data.
- **CLI & Module Support**: Installable via `pip` and runnable directly from the command line.

---

## 🛠️ Installation

### Option A: From PyPI

```bash
pip install svg2gif
playwright install chromium
```

---

## 💻 Developer Setup / Installing from Source

If you want to contribute, modify the code, or install directly from the source repository:

### 1. Clone the repository
```bash
git clone https://github.com/ishandutta2007/svg2gif.git
cd svg2gif
```

### 2. Set up an isolated environment

#### Option 1: Standard `venv`
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

#### Option 2: `pyenv` / `pyenv-virtualenv`
```bash
# Install desired Python version and create virtualenv
pyenv install 3.11.9  # or any supported Python 3.7+ version
pyenv virtualenv 3.11.9 svg2gif-env

# Activate for current directory
pyenv local svg2gif-env
```

### 3. Install in editable mode
Installing in editable (`-e`) mode lets you run `svg2gif` as a CLI command while immediately reflecting any code changes you make:
```bash
pip install -e .
```

Alternatively, install dependencies via `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Chromium browser
```bash
playwright install chromium
```

---

## 🚀 Usage

### Command Line Interface (CLI)

Once installed, use the `svg2gif` CLI binary anywhere:

```bash
svg2gif path/to/input.svg path/to/output.gif
```

#### CLI Options

```text
usage: svg2gif [-h] [-d DURATION] [-f FPS] [-w MAX_WIDTH] input output

Convert animated SVG files into optimized looping animated GIFs.

positional arguments:
  input                 Path to input .svg file
  output                Path to output .gif file

options:
  -h, --help            show this help message and exit
  -d, --duration DURATION
                        Duration of the animation capture loop in seconds (default: 3.0)
  -f, --fps FPS         Frames per second (default: 30)
  -w, --max-width MAX_WIDTH
                        Maximum width for output GIF (default: 640)
```

Example with custom flags:
```bash
svg2gif input.svg output.gif -d 5.0 -f 24 -w 800
```

---

### Python API

You can also import and use `svg2gif` in your Python scripts:

```python
from svg2gif import convert_animated_svg_to_gif

convert_animated_svg_to_gif(
    svg_path="input.svg",
    output_gif_path="output.gif",
    duration_seconds=3.0,  # Duration of the capture loop in seconds
    fps=30,                # Frames per second
    max_width=640          # Optional max width resizing
)
```

---

## 📦 Building & Publishing to PyPI

To build distribution packages and publish to PyPI:

1. Install build tools:
   ```bash
   pip install build twine
   ```

2. Build source archive and wheel:
   ```bash
   python -m build
   ```

3. Upload package to PyPI:
   ```bash
   twine upload dist/*
   ```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](file:///C:/Users/ishan/Documents/Projects/svg2gif/LICENSE) file for details.

---

## ⭐ Star History

<a href="https://star-history.com/#ishandutta2007/svg2gif&Timeline" align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/ishandutta2007_svg2gif_growth.svg">
    <img alt="Star History Chart" src="assets/ishandutta2007_svg2gif_growth.svg">
  </picture>
</a>
