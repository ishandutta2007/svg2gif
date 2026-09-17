import os
import sys
import unittest
import argparse
from PIL import Image

# Import functions from svg2gif
from svg2gif import (
    parse_file_size,
    detect_svg_animation_durations,
    calculate_optimal_fps_duration,
    convert_animated_svg_to_gif,
)

class TestSvg2GifMaxFileSize(unittest.TestCase):

    def test_parse_file_size(self):
        self.assertIsNone(parse_file_size(None))
        self.assertEqual(parse_file_size(1.2), 1.2)
        self.assertEqual(parse_file_size(2), 2.0)
        self.assertEqual(parse_file_size("1.2"), 1.2)
        self.assertEqual(parse_file_size("1.2MB"), 1.2)
        self.assertEqual(parse_file_size("1.2mb"), 1.2)
        self.assertEqual(parse_file_size("1.5M"), 1.5)
        self.assertAlmostEqual(parse_file_size("800KB"), 800 / 1024.0)
        self.assertAlmostEqual(parse_file_size("800K"), 800 / 1024.0)
        self.assertAlmostEqual(parse_file_size("1048576B"), 1.0)

        # Invalid formats
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_file_size("invalid")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_file_size("0")
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_file_size("-1.5MB")

    def test_detect_svg_animation_durations(self):
        svg_sample = """
        <svg xmlns="http://www.w3.org/2000/svg">
            <style>
                .a { animation: spin 3s linear infinite; }
                .b { animation-duration: 2500ms; }
            </style>
            <rect width="10" height="10">
                <animate dur="4s" attributeName="x" />
            </rect>
        </svg>
        """
        durations = detect_svg_animation_durations(svg_sample)
        self.assertIn(3.0, durations)
        self.assertIn(2.5, durations)
        self.assertIn(4.0, durations)

    def test_calculate_optimal_fps_duration_balanced(self):
        # Frame metrics typical of banner.svg
        bytes_per_frame = 40000
        base_overhead = 10000
        max_file_size_mb = 1.2

        fps, duration, total_frames = calculate_optimal_fps_duration(
            max_file_size_mb=max_file_size_mb,
            bytes_per_frame=bytes_per_frame,
            base_overhead=base_overhead,
            detected_svg_durations=[2.0, 3.0, 4.0]
        )

        # Check total estimated size is within limit
        est_bytes = base_overhead + total_frames * bytes_per_frame
        est_mb = est_bytes / (1024 * 1024)
        self.assertLessEqual(est_mb, max_file_size_mb)

        # Check that wise choices were made (neither fps nor duration is extreme)
        # fps should not be 2 (slideshow) or 24+ with 1s duration
        self.assertGreaterEqual(fps, 8, "FPS should not be too low (e.g. fps=2)")
        self.assertLessEqual(fps, 20, "FPS should not be excessively high")
        self.assertGreaterEqual(duration, 1.75, "Duration should not be too short (e.g. dur=1s)")
        self.assertLessEqual(duration, 5.0, "Duration should not be too long (e.g. dur=10s)")

    def test_end_to_end_conversion_with_max_size(self):
        svg_path = os.path.join(os.path.dirname(__file__), "assets", "banner.svg")
        out_gif = os.path.join(os.path.dirname(__file__), "assets", "test_e2e_maxsize.gif")

        try:
            # We pass max_file_size=1.2, but intentionally pass conflicting fps=60 and duration_seconds=15.0
            # to verify that they are properly overridden and ignored
            convert_animated_svg_to_gif(
                svg_path=svg_path,
                output_gif_path=out_gif,
                duration_seconds=15.0,
                fps=60,
                max_width=640,
                max_file_size=1.2
            )

            self.assertTrue(os.path.exists(out_gif), "Output GIF must exist")
            file_size_mb = os.path.getsize(out_gif) / (1024 * 1024)
            self.assertLessEqual(file_size_mb, 1.2, f"Final size {file_size_mb:.2f} MB must be <= 1.2 MB")
            self.assertGreater(file_size_mb, 0.5, "Final size should utilize a good portion of the limit")

            # Verify the resulting GIF can be opened and has frames
            with Image.open(out_gif) as img:
                self.assertTrue(img.is_animated)
                self.assertGreater(img.n_frames, 5)
        finally:
            if os.path.exists(out_gif):
                os.remove(out_gif)

    def test_svg2gifpy_alias_import(self):
        import svg2gifpy
        self.assertTrue(callable(svg2gifpy.convert_animated_svg_to_gif))
        self.assertTrue(callable(svg2gifpy.main))
        self.assertTrue(callable(svg2gifpy.parse_file_size))

    def test_cli_interactive_module(self):
        import cli_interactive
        link = cli_interactive.format_clickable_link("https://github.com/ishandutta2007/svg2gif")
        self.assertIn("https://github.com/ishandutta2007/svg2gif", link)
        self.assertIn("\x1b]8;;", link)

        # Ensure handle_interactive_completion does not block in automated/non-interactive test runs
        cli_interactive.handle_interactive_completion(
            "https://github.com/ishandutta2007/svg2gif",
            "https://github.com/sponsors/ishandutta2007"
        )

if __name__ == "__main__":
    unittest.main()
