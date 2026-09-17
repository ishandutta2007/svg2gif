"""
svg2gif - A CLI tool and Python library for converting animated SVG files into optimized animated GIFs.
"""

import os
import sys
import re
import math
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

def parse_file_size(val):
    """
    Parses a file size representation (e.g. 1.2, '1.2', '1.2MB', '800KB') into float MB.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        res = float(val)
    else:
        s = str(val).strip().upper()
        if not s:
            return None
        try:
            if s.endswith("MB"):
                res = float(s[:-2].strip())
            elif s.endswith("M"):
                res = float(s[:-1].strip())
            elif s.endswith("KB"):
                res = float(s[:-2].strip()) / 1024.0
            elif s.endswith("K"):
                res = float(s[:-1].strip()) / 1024.0
            elif s.endswith("B"):
                res = float(s[:-1].strip()) / (1024.0 * 1024.0)
            else:
                res = float(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid file size format: '{val}'. Expected e.g. 1.2, 1.2MB, or 800KB.")
            
    if res <= 0:
        raise argparse.ArgumentTypeError(f"File size limit must be greater than 0, got {val}")
    return res

def detect_svg_animation_durations(svg_content):
    """
    Scans SVG markup for declared CSS animation durations and SMIL 'dur' attributes.
    Returns a sorted list of unique animation cycle lengths in seconds.
    """
    durations = []
    css_patterns = [
        r'\banimation(?:-duration)?\s*:[^;]*?\b(\d+(?:\.\d+)?)\s*(s|ms)\b',
        r'--[\w-]*duration\s*:\s*(\d+(?:\.\d+)?)\s*(s|ms)\b',
    ]
    for pattern in css_patterns:
        for val, unit in re.findall(pattern, svg_content, re.IGNORECASE):
            d = float(val)
            if unit.lower() == 'ms':
                d /= 1000.0
            if 0.1 <= d <= 30.0:
                durations.append(round(d, 3))

    smil_pattern = r'\bdur\s*=\s*["\'](\d+(?:\.\d+)?)\s*(s|ms)["\']'
    for val, unit in re.findall(smil_pattern, svg_content, re.IGNORECASE):
        d = float(val)
        if unit.lower() == 'ms':
            d /= 1000.0
        if 0.1 <= d <= 30.0:
            durations.append(round(d, 3))

    return sorted(list(set(durations)))

def probe_frame_metrics(page, max_width=640):
    """
    Captures a minimal sample directly from the browser page to determine
    the average compressed frame size and base GIF overhead for this specific SVG.
    """
    sample_frames = []
    for _ in range(2):
        screenshot_bytes = page.locator("svg").screenshot(omit_background=True)
        img = Image.open(BytesIO(screenshot_bytes))
        sample_frames.append(img.convert("RGB"))
        time.sleep(0.1)

    if max_width and sample_frames[0].width > max_width:
        scale = max_width / sample_frames[0].width
        new_size = (max_width, int(sample_frames[0].height * scale))
        sample_frames = [img.resize(new_size, Image.Resampling.LANCZOS) for img in sample_frames]

    optimized = [img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256) for img in sample_frames]

    b1 = BytesIO()
    optimized[0].save(b1, format="GIF", optimize=True)
    size1 = b1.tell()

    b2 = BytesIO()
    optimized[0].save(b2, format="GIF", save_all=True, append_images=optimized[1:2], duration=100, optimize=True)
    size2 = b2.tell()

    bytes_per_frame = max(1000, size2 - size1)
    base_overhead = max(500, size1 - bytes_per_frame)
    return bytes_per_frame, base_overhead

def calculate_optimal_fps_duration(max_file_size_mb, bytes_per_frame, base_overhead=10000, detected_svg_durations=None):
    """
    Calculates the optimal (fps, duration, total_frames) combination such that:
    1. The generated file size is as high as possible within max_file_size_mb limit.
    2. The (fps, duration) pair is well-balanced (neither has too high nor too low of either fps or duration).
    """
    import math
    max_bytes = max_file_size_mb * 1024 * 1024
    target_bytes = max_bytes * 0.92  # 8% safety margin against compression variances

    max_frames = int((target_bytes - base_overhead) / bytes_per_frame)
    max_frames = max(4, max_frames)

    # Ideal anchors
    anchor_dur = 2.5
    if detected_svg_durations:
        suitable = [d for d in detected_svg_durations if 1.5 <= d <= 4.5]
        if suitable:
            # Pick duration closest to 2.5s - 3.0s sweet spot
            anchor_dur = min(suitable, key=lambda d: abs(d - 2.8))

    anchor_fps = 10.0

    # Grid of candidate FPS and clean duration steps
    fps_options = list(range(4, 31))
    dur_options = [round(x * 0.25, 2) for x in range(4, 33)]  # 1.00s to 8.00s
    if detected_svg_durations:
        for d in detected_svg_durations:
            if 1.0 <= d <= 8.0 and d not in dur_options:
                dur_options.append(d)
        dur_options.sort()

    candidates = []
    for fps in fps_options:
        for dur in dur_options:
            total_frames = int(round(fps * dur))
            if total_frames < 4 or total_frames > max_frames:
                continue

            est_bytes = base_overhead + total_frames * bytes_per_frame
            if est_bytes > max_bytes:
                continue

            utilization = est_bytes / max_bytes

            # Heavily penalize unbalanced pairs:
            # 1. FPS extremes:
            # If fps is too low (< 8), video becomes a choppy slideshow.
            # If fps is too high (> 18), frames are wasted when duration could be better.
            fps_penalty = 0.0
            if fps < 8:
                fps_penalty = (8 - fps) ** 2 * 2.0
            elif fps > 18:
                fps_penalty = (fps - 18) ** 1.5 * 0.5

            # 2. Duration extremes:
            # If duration is too low (< 2.0s), animation cuts off prematurely.
            # If duration is too high (> 4.0s), animation drags and fps is squeezed.
            dur_penalty = 0.0
            if dur < 2.0:
                dur_penalty = ((2.0 - dur) * 4) ** 2 * 2.0
            elif dur > 4.0:
                dur_penalty = (dur - 4.0) ** 1.5 * 0.5

            center_dev = (math.log(fps / anchor_fps)) ** 2 + (math.log(dur / anchor_dur)) ** 2
            balance_score = -(fps_penalty + dur_penalty + center_dev)

            # Bonus for alignment with detected SVG animation cycles or clean multiples
            cycle_bonus = 0.0
            if detected_svg_durations and any(abs(dur - d) < 0.01 for d in detected_svg_durations):
                cycle_bonus += 0.05
            if abs(dur - round(dur * 2) / 2) < 0.01:
                cycle_bonus += 0.02

            # Combined score: prioritize balance and maximize size utilization
            score = utilization + (0.05 * balance_score) + cycle_bonus
            candidates.append((score, fps, dur, total_frames, est_bytes))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0]
        return best[1], best[2], best[3]

    # Minimal fallback for extremely constrained size limits
    min_fps = 6
    min_dur = 1.5
    return min_fps, min_dur, int(round(min_fps * min_dur))

def convert_animated_svg_to_gif(svg_path, output_gif_path, duration_seconds=3.0, fps=30, max_width=640, max_file_size=None):
    """
    Renders an animated SVG in a headless browser, captures frames, 
    and saves them as an optimized animated GIF.

    :param svg_path: Path to the source input SVG file.
    :param output_gif_path: Target path for the output GIF file.
    :param duration_seconds: Capture duration in seconds (default: 3.0).
                             Ignored if max_file_size is specified.
    :param fps: Frames captured per second (default: 30).
                Ignored if max_file_size is specified.
    :param max_width: Max pixel width for output GIF downscaling (default: 640).
    :param max_file_size: Maximum output GIF file size in MB (e.g. 1.2 or '800KB').
                          When provided, automatically calculates optimal (fps, duration)
                          to maximize file size within this limit.
    """
    max_file_size_mb = parse_file_size(max_file_size)
    print(f"Converting {svg_path} to {output_gif_path}")
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

        if max_file_size_mb is not None:
            print(f"Target max file size: {max_file_size_mb:.2f} MB. Ignoring manual fps and duration...")
            bpf, base = probe_frame_metrics(page, max_width)
            detected_durs = detect_svg_animation_durations(svg_content)
            fps, duration_seconds, total_frames = calculate_optimal_fps_duration(
                max_file_size_mb, bpf, base, detected_durs
            )
            frame_delay = int(1000 / fps)
            print(
                f"Selected optimal configuration: FPS={fps}, "
                f"Duration={duration_seconds:.2f}s, Delay={frame_delay}ms (Total frames: {total_frames})"
            )
            # Reset page content for clean capture starting at t=0
            page.set_content(html_content)
            time.sleep(0.1)
        else:
            frame_delay = int(1000 / fps)
            total_frames = int(duration_seconds * fps)

        print(f"Capturing {total_frames} frames at {fps} FPS...")

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

        # Post-save safeguard: if max_file_size was set and file slightly exceeded, trim trailing frames
        if max_file_size_mb is not None:
            while file_size_mb > max_file_size_mb and len(optimized_frames) > 2:
                print(f"File size {file_size_mb:.2f} MB slightly exceeds limit {max_file_size_mb:.2f} MB. Trimming frame to fit...")
                optimized_frames = optimized_frames[:-1]
                optimized_frames[0].save(
                    output_gif_path,
                    save_all=True,
                    append_images=optimized_frames[1:],
                    duration=frame_delay,
                    loop=0,
                    optimize=True
                )
                file_size_mb = os.path.getsize(output_gif_path) / (1024 * 1024)

            print(f"Done! Final File Size: {file_size_mb:.2f} MB (Limit: {max_file_size_mb:.2f} MB)")
        else:
            print(f"Done! Final File Size: {file_size_mb:.2f} MB")
            if file_size_mb > 1.0:
                print("⚠️ Warning: File is still over 1MB. Reduce FPS or total duration.")

def format_clickable_link(url: str, label: str | None = None) -> str:
    """Format a URL as a styled clickable terminal hyperlink using ANSI OSC 8 escape sequences and SGR styling."""
    if label is None:
        label = url
    if sys.platform == "win32":
        try:
            import os
            os.system("")
        except Exception:
            pass
    # \x1b]8;;URL\x07 renders hyperlink in OSC 8 terminals (Windows Terminal, VS Code, etc.)
    # \x1b[4;36m renders cyan underlined text in ANSI terminals (PowerShell 6/7, ConHost, etc.)
    return f"\x1b]8;;{url}\x07\x1b[4;36m{label}\x1b[0m\x1b]8;;\x07"


def main():
    default_input = os.path.join(os.getcwd(), "assets", "banner.svg")
    if not os.path.exists(default_input):
        script_dir_banner = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "banner.svg")
        if os.path.exists(script_dir_banner):
            default_input = script_dir_banner

    default_output = os.path.join(os.getcwd(), "assets", "social-preview.gif")

    parser = argparse.ArgumentParser(
        description="Convert animated SVG files into optimized looping animated GIFs."
    )
    parser.add_argument("-i", "--input", default=default_input, help="Path to input .svg file")
    parser.add_argument("-o", "--output", default=default_output, help="Path to output .gif file")
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
    parser.add_argument(
        "-s", "--max-file-size", "--max-size",
        type=parse_file_size,
        default=None,
        dest="max_file_size",
        help="Maximum output GIF file size in MB (e.g. 1.2 or 1.2MB). "
             "When set, overrides and ignores --fps and --duration to automatically "
             "calculate the optimal balanced (fps, duration) pair within this limit."
    )

    args = parser.parse_args()
    try:
        convert_animated_svg_to_gif(
            svg_path=args.input,
            output_gif_path=args.output,
            duration_seconds=args.duration,
            fps=args.fps,
            max_width=args.max_width,
            max_file_size=args.max_file_size
        )
        repo_link = format_clickable_link("https://github.com/ishandutta2007/svg2gif")
        sponsor_link = format_clickable_link("https://github.com/sponsors/ishandutta2007")

        print("\n" + "=" * 60)
        print("Thank you for using svg2gifpy!")
        print("Found it helpful? Please star, fork & share the repo:")
        print(f"   {repo_link}")
        print("Support development / Buy me a coffee:")
        print(f"   {sponsor_link}")
        print("=" * 60)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
