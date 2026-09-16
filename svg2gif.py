"""
svg2gif - A CLI tool and Python library for converting animated SVG files into optimized animated GIFs.
"""

import os
import sys
import time
import argparse
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright
import xml.etree.ElementTree as ET

def get_svg_dimensions(file_path):
    """Parses SVG to find viewBox or width/height dimensions."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    tag = root.tag.split('}')[-1]
    if tag != 'svg':
        return None, None

    viewbox = root.get('viewBox')
    if viewbox:
        try:
            parts = [float(x) for x in viewbox.replace(',', ' ').split() if x]
            if len(parts) >= 4:
                return parts[2], parts[3]
        except ValueError:
            pass

    try:
        w = float(root.get('width', 0).replace('px', ''))
        h = float(root.get('height', 0).replace('px', ''))
        if w > 0 and h > 0:
            return w, h
    except ValueError:
        pass

    return None, None

def print_svg_aspect_ratio(file_path):
    w, h = get_svg_dimensions(file_path)
    if w and h:
        ratio = w / h
        print(f"SVG Width: {w}, Height: {h}")
        print(f"SVG Aspect Ratio (W/H): {ratio:.4f}")
    else:
        print("SVG: Could not determine valid dimensions or viewBox.")

def convert_animated_svg_to_gif(svg_path, output_gif_path, duration_seconds=3.0, fps=30, max_width=640):
    """
    Renders an animated SVG in a headless browser, captures frames, 
    and saves them as an optimized animated GIF.

    :param svg_path: Path to the source input SVG file.
    :param output_gif_path: Target path for the output GIF file.
    :param duration_seconds: Capture duration in seconds (default: 3.0).
    :param fps: Frames captured per second (default: 30).
    :param max_width: Max pixel width for output GIF downscaling (default: 640).
    """
    if not os.path.exists(svg_path):
        raise FileNotFoundError(f"Input SVG file not found: {svg_path}")

    print_svg_aspect_ratio(svg_path)
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    # Wrap SVG in a minimal HTML container to ensure proper rendering bounds
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body, html {{ margin: 0; padding: 0; overflow: hidden; background: transparent; }}
            svg {{ display: block; width: 100vw; height: 100vh; }}
        </style>
    </head>
    <body>
        {svg_content}
    </body>
    </html>
    """

    frames = []
    frame_delay = int(1000 / fps)  # Milliseconds per frame for the GIF output
    total_frames = int(duration_seconds * fps)

    print(f"Capturing {total_frames} frames at {fps} FPS...")

    with sync_playwright() as p:
        # Launch headless browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Load the HTML string natively
        page.set_content(html_content)
        
        # Give the browser a split second to compute initial layouts
        time.sleep(0.2)

        # Extract actual SVG dimensions for an exact screenshot crop
        dimensions = page.evaluate("""() => {
            const svg = document.querySelector('svg');
            return {
                width: svg.clientWidth || parseInt(svg.getAttribute('width')) || 500,
                height: svg.clientHeight || parseInt(svg.getAttribute('height')) || 500
            };
        }""")
        
        page.set_viewport_size({"width": dimensions["width"], "height": dimensions["height"]})

        # Capture the image sequence loop
        start_time = time.time()
        for i in range(total_frames):
            screenshot_bytes = page.locator("svg").screenshot(omit_background=True)
            img = Image.open(BytesIO(screenshot_bytes))
            
            frames.append(img.convert("RGB"))
            
            # Calculate dynamic wait to maintain target FPS pace
            expected_time = start_time + (i + 1) / fps
            sleep_time = expected_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

        browser.close()

    # Save the accumulated frames into a looping animated GIF
    if frames:
        print(f"Compiling and compressing frames into {output_gif_path}...")
        
        # --- OPTIMIZATION STEP 1: Downscale dimensions if requested ---
        first_frame = frames[0]
        if max_width and first_frame.width > max_width:
            scale_factor = max_width / first_frame.width
            new_size = (max_width, int(first_frame.height * scale_factor))
            frames = [img.resize(new_size, Image.Resampling.LANCZOS) for img in frames]

        # --- OPTIMIZATION STEP 2: Quantize and Optimize Palette ---
        optimized_frames = []
        for img in frames:
            paletted_img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            optimized_frames.append(paletted_img)

        # Ensure target output directory exists
        out_dir = os.path.dirname(os.path.abspath(output_gif_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # --- OPTIMIZATION STEP 3: Save with Pillow's compression engine ---
        optimized_frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=optimized_frames[1:],
            duration=frame_delay,
            loop=0,
            optimize=True
        )
        
        file_size_mb = os.path.getsize(output_gif_path) / (1024 * 1024)
        print(f"Done! Final File Size: {file_size_mb:.2f} MB")
        
        if file_size_mb > 1.0:
            print("⚠️ Warning: File is still over 1MB. Reduce FPS or total duration.")

def main():
    parser = argparse.ArgumentParser(
        description="Convert animated SVG files into optimized looping animated GIFs."
    )
    parser.add_argument("input", help="Path to input .svg file")
    parser.add_argument("output", help="Path to output .gif file")
    parser.add_argument(
        "-d", "--duration", type=float, default=3.0,
        help="Duration of the animation capture loop in seconds (default: 3.0)"
    )
    parser.add_argument(
        "-f", "--fps", type=int, default=30,
        help="Frames per second (default: 30)"
    )
    parser.add_argument(
        "-w", "--max-width", type=int, default=640,
        help="Maximum width for output GIF (default: 640)"
    )

    args = parser.parse_args()
    
    try:
        convert_animated_svg_to_gif(
            svg_path=args.input,
            output_gif_path=args.output,
            duration_seconds=args.duration,
            fps=args.fps,
            max_width=args.max_width
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
