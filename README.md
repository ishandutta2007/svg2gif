# svg2gif 🎨➡️🎬

A high-performance Python tool for converting animated SVG files into optimized, looping animated GIFs using headless Playwright and Pillow.

---

## ✨ Features

- **Headless Browser Rendering**: Accurate rendering of CSS animations, SMIL, and JavaScript-driven SVG animations using Playwright (Chromium).
- **Aspect Ratio Preservation**: Automatically detects SVG viewBox/dimensions to maintain precise aspect ratios during frame capture.
- **Smart Optimization Engine**:
  - **Downscaling**: Automatically resizes large SVGs to ideal max-width parameters for smaller file outputs.
  - **Palette Quantization**: Applies 256-color adaptive palette conversion per frame.
  - **Frame Compression**: Leverages Pillow's optimization to discard redundant frame data.
- **CLI & Module Support**: Run directly via command-line arguments or import into Python scripts.

---

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/ishandutta2007/svg2gif.git
cd svg2gif
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Playwright browser binaries
```bash
playwright install chromium
```

---

## 🚀 Usage

### Command Line

Run `svg2gif.py` directly by supplying input SVG and output GIF paths:

```bash
python svg2gif.py path/to/input.svg path/to/output.gif
```

If no arguments are provided, it defaults to converting `assets/banner.svg` into `assets/social-preview.gif`.

### Python API

```python
from svg2gif import convert_animated_svg_to_gif

convert_animated_svg_to_gif(
    svg_path="input.svg",
    output_gif_path="output.gif",
    duration_seconds=3.0,  # Duration of the capture loop in seconds
    fps=30                 # Frames per second
)
```

---

## ⚙️ How It Works

1. **SVG Analysis**: Parses the SVG XML to retrieve viewBox or width/height attributes.
2. **Headless Execution**: Loads the SVG inside a headless Chromium page.
3. **Frame Capture Loop**: Takes sequential in-memory screenshots synchronized to the target FPS.
4. **GIF Compilation**: Downscales frame dimensions if necessary, applies adaptive palette quantization, and exports an optimized looping GIF.

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

