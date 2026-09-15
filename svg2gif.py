import os
import time
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright

def convert_animated_svg_to_gif(svg_path, output_gif_path, duration_seconds=3.0, fps=30):
    """
    Renders an animated SVG in a headless browser, captures frames, 
    and saves them as an animated GIF.
    """
    # Read the SVG content
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
        print(f"Compiling frames into {output_gif_path}...")
        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_delay,  # Duration of each frame in milliseconds
            loop=0                 # 0 means loop infinitely
        )
        print("Done!")
    else:
        print("Failed to capture frames.")

# --- Usage Example ---
convert_animated_svg_to_gif(
    svg_path="banner.svg", 
    output_gif_path="perfect_animation.gif", 
    duration_seconds=4.0,  # Match this roughly to your SVG's animation cycle
    fps=25                 # Standard smooth animation frame rate
)
