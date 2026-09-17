"""
svg2gifpy - Python library and CLI tool for converting animated SVG files into optimized animated GIFs.
"""

from svg2gif import *
from svg2gif import (
    main,
    convert_animated_svg_to_gif,
    parse_file_size,
    detect_svg_animation_durations,
    probe_frame_metrics,
    calculate_optimal_fps_duration,
    get_svg_dimensions,
    print_svg_aspect_ratio,
)

if __name__ == "__main__":
    main()
