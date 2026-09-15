import os
import time
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright
import xml.etree.ElementTree as ET

def print_svg_aspect_ratio(file_path):
    # Parse the SVG file
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Strip namespace if present (e.g., '{http://w3.org}svg')
    tag = root.tag.split('}')[-1]
    if tag != 'svg':
        print("Error: Not a valid SVG root element.")
        return

    # Check for viewBox first (most reliable for aspect ratio)
    viewbox = root.get('viewBox')
    if viewbox:
        _, _, w, h = map(float, viewbox.replace(',', ' ').split())
    else:
        # Fallback to width and height attributes
        w = float(root.get('width', 0).replace('px', ''))
        h = float(root.get('height', 0).replace('px', ''))

    if w > 0 and h > 0:
        ratio = w / h
        print(f"SVG Width: {w}, Height: {h}")
        print(f"SVG Aspect Ratio (W/H): {ratio:.4f}")
    else:
        print("SVG: Could not determine valid dimensions or viewBox.")

def convert_animated_svg_to_gif(svg_path, output_gif_path, duration_seconds=3.0, fps=30):
    """
    Renders an animated SVG in a headless browser, captures frames, 
    and saves them as an animated GIF.
    """
    # Read the SVG content
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
            # Take in-memory screenshot of the exact element bounds
            screenshot_bytes = page.locator("svg").screenshot(omit_background=True)
            img = Image.open(BytesIO(screenshot_bytes))
            
            # GIFs do not support true alpha channels well, so convert to Palette mode
            # If your SVG relies on transparent background, remove the .convert("RGB")
            frames.append(img.convert("RGB"))
            
            # Calculate dynamic wait to maintain targeting FPS pace
            expected_time = start_time + (i + 1) / fps
            sleep_time = expected_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

        browser.close()

    # Save the accumulated frames into a looping animated GIF
    if frames:
        print(f"Compiling and compressing frames into {output_gif_path}...")
        
        # --- OPTIMIZATION STEP 1: Downscale dimensions if the source is massive ---
        # GIFs compress poorly at high resolutions. 500-600px max width is ideal.
        MAX_WIDTH = 640 
        print("height before", frames[0].height)
        print(f"aspect ratio before: {(frames[0].width/frames[0].height):.4f}")
        first_frame = frames[0]
        if first_frame.width > MAX_WIDTH:
            scale_factor = MAX_WIDTH / first_frame.width
            print("scale_factor", scale_factor)
            new_size = (MAX_WIDTH, int(first_frame.height * scale_factor))
            frames = [img.resize(new_size, Image.Resampling.LANCZOS) for img in frames]

        # --- OPTIMIZATION STEP 2: Quantize and Optimize Palette ---
        # Convert images to Palette mode ('P') with an adaptive 256-color map.
        # This reduces data size per frame dramatically.
        print("height after", frames[0].height)
        print(f"aspect ratio after: {(frames[0].width/frames[0].height):.4f}")
        optimized_frames = []
        for img in frames:
            # 'adaptive' creates a custom palette optimized for your SVG's exact colors
            paletted_img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            optimized_frames.append(paletted_img)

        # --- OPTIMIZATION STEP 3: Save with Pillow's compression engine ---
        optimized_frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=optimized_frames[1:],
            duration=frame_delay,
            loop=0,
            optimize=True  # <-- Crucial: Removes redundant pixel data between frames
        )
        
        # Check the final file size
        file_size_mb = os.path.getsize(output_gif_path) / (1024 * 1024)
        print(f"Done! Final File Size: {file_size_mb:.2f} MB")
        
        if file_size_mb > 1.0:
            print("⚠️ Warning: File is still over 1MB. Reduce FPS or total duration_seconds.")

# --- Usage Example ---
convert_animated_svg_to_gif(
    svg_path="banner.svg", 
    output_gif_path="perfect_animation.gif", 
    duration_seconds=2.8,  # Match this roughly to your SVG's animation cycle
    fps=8                 # Standard smooth animation frame rate
)
