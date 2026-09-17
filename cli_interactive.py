"""
cli_interactive.py - Terminal hyperlink and interactive completion handling for svg2gifpy.

Provides cross-platform support for:
- Terminal OSC 8 hyperlinks (Windows Terminal, VS Code, iTerm, etc.)
- ANSI SGR styling for legacy and modern terminals
- Native Win32 Console API mouse click detection in legacy Windows conhost.exe
- Single-key shortcuts ([1]/[s], [2]/[c], [Enter]/[q]) to open URLs in browser
- Safe non-interactive bypass for CI/CD and scripted environments
"""

import os
import sys
import time
import webbrowser


def format_clickable_link(url: str, label: str | None = None) -> str:
    """Format a URL as a styled clickable terminal hyperlink using ANSI OSC 8 escape sequences and SGR styling."""
    if label is None:
        label = url
    if sys.platform == "win32":
        try:
            os.system("")
        except Exception:
            pass
    # \x1b[4;36m renders cyan underlined text in ANSI terminals (PowerShell 6/7, ConHost, etc.)
    # \x1b]8;;URL\x07 renders hyperlink in OSC 8 terminals (Windows Terminal, VS Code, etc.)
    return f"\x1b[4;36m\x1b]8;;{url}\x07{label}\x1b]8;;\x07\x1b[0m"


def handle_interactive_completion(repo_url: str, sponsor_url: str):
    """
    Provides a generic, interactive completion experience across all terminals
    (including legacy Windows conhost.exe, Windows Terminal, PowerShell 6/7, and POSIX terminals).
    Allows opening links via:
      - Direct mouse click on option [1] / repo line or [2] / sponsor line (handled natively via Win32 Console API on conhost)
      - Single-key press ([1]/[s], [2]/[c])
      - Enter / Esc / Space to exit
    Supports multiple clicks/keypresses without exiting prematurely.
    Bypasses automatically in non-interactive / CI environments.
    """
    if not (hasattr(sys, "stdin") and sys.stdin and sys.stdin.isatty() and
            hasattr(sys, "stdout") and sys.stdout and sys.stdout.isatty()):
        return

    prompt_bar = (
        "  \x1b[1;36m[1] Open GitHub Repo\x1b[0m   "
        "\x1b[1;32m[2] Sponsor / Coffee\x1b[0m   "
        "\x1b[90m[Enter to exit]\x1b[0m: "
    )
    print(prompt_bar, end="", flush=True)

    # Enable SGR mouse tracking for modern terminals that forward mouse events
    sys.stdout.write("\x1b[?1000h\x1b[?1006h")
    sys.stdout.flush()

    try:
        if sys.platform == "win32":
            _run_windows_interactive_loop(repo_url, sponsor_url)
        else:
            _run_posix_interactive_loop(repo_url, sponsor_url)
    except Exception:
        pass
    finally:
        # Disable SGR mouse tracking and print clean newline
        sys.stdout.write("\x1b[?1006l\x1b[?1000l\r\x1b[K\n")
        sys.stdout.flush()


def _open_url_safely(url: str, label: str):
    """Prints confirmation and opens the URL in the default browser."""
    print(
        f"\r  \x1b[32m✔ Opened {label}!\x1b[0m   "
        f"[1] Open GitHub Repo   [2] Sponsor / Coffee   "
        f"\x1b[90m[Enter to exit]\x1b[0m: ",
        end="",
        flush=True
    )
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _run_windows_interactive_loop(repo_url: str, sponsor_url: str):
    """Win32 console event loop supporting native mouse clicks and keyboard events in conhost.exe."""
    import ctypes
    from ctypes import wintypes

    class COORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    class KEY_EVENT_RECORD(ctypes.Structure):
        _fields_ = [
            ("bKeyDown", wintypes.BOOL),
            ("wRepeatCount", wintypes.WORD),
            ("wVirtualKeyCode", wintypes.WORD),
            ("wVirtualScanCode", wintypes.WORD),
            ("uChar", wintypes.WCHAR),
            ("dwControlKeyState", wintypes.DWORD),
        ]

    class MOUSE_EVENT_RECORD(ctypes.Structure):
        _fields_ = [
            ("dwMousePosition", COORD),
            ("dwButtonState", wintypes.DWORD),
            ("dwControlKeyState", wintypes.DWORD),
            ("dwEventFlags", wintypes.DWORD),
        ]

    class EVENT_UNION(ctypes.Union):
        _fields_ = [
            ("KeyEvent", KEY_EVENT_RECORD),
            ("MouseEvent", MOUSE_EVENT_RECORD),
            ("WindowBufferSizeEvent", COORD),
            ("MenuEvent", wintypes.UINT),
            ("FocusEvent", wintypes.BOOL),
        ]

    class INPUT_RECORD(ctypes.Structure):
        _fields_ = [
            ("EventType", wintypes.WORD),
            ("Event", EVENT_UNION),
        ]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [
            ("Left", wintypes.SHORT),
            ("Top", wintypes.SHORT),
            ("Right", wintypes.SHORT),
            ("Bottom", wintypes.SHORT),
        ]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]

    kernel32 = ctypes.windll.kernel32
    GENERIC_RW = 0xC0000000
    SHARE_RW = 3
    OPEN_EXISTING = 3

    hConIn = kernel32.CreateFileW("CONIN$", GENERIC_RW, SHARE_RW, None, OPEN_EXISTING, 0, None)
    hConOut = kernel32.CreateFileW("CONOUT$", GENERIC_RW, SHARE_RW, None, OPEN_EXISTING, 0, None)

    prompt_y = -1
    if hConOut and hConOut != -1:
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if kernel32.GetConsoleScreenBufferInfo(hConOut, ctypes.byref(csbi)):
            prompt_y = csbi.dwCursorPosition.Y

    orig_mode = wintypes.DWORD()
    if hConIn and hConIn != -1:
        kernel32.GetConsoleMode(hConIn, ctypes.byref(orig_mode))
        # Disable QuickEdit (0x0040), enable Mouse Input (0x0010) and Extended Flags (0x0080)
        new_mode = (orig_mode.value & ~0x0040) | 0x0080 | 0x0010
        kernel32.SetConsoleMode(hConIn, new_mode)

    try:
        start_time = time.time()
        records = (INPUT_RECORD * 1)()
        num_read = wintypes.DWORD()
        last_click_time = 0.0
        prev_button_state = False

        while time.time() - start_time < 30.0:
            res = kernel32.WaitForSingleObject(hConIn, 50)
            if res == 0:  # WAIT_OBJECT_0
                num_events = wintypes.DWORD()
                kernel32.GetNumberOfConsoleInputEvents(hConIn, ctypes.byref(num_events))
                if num_events.value == 0:
                    continue
                if kernel32.ReadConsoleInputW(hConIn, records, 1, ctypes.byref(num_read)) and num_read.value > 0:
                    rec = records[0]
                    if rec.EventType == 1:  # KEY_EVENT
                        key = rec.Event.KeyEvent
                        if key.bKeyDown:
                            ch = key.uChar
                            if ch in ('1', 's', 'S'):
                                start_time = time.time()
                                _open_url_safely(repo_url, "GitHub Repo")
                            elif ch in ('2', 'c', 'C'):
                                start_time = time.time()
                                _open_url_safely(sponsor_url, "Sponsor Dashboard")
                            elif ch in ('\r', '\n', '\x1b', 'q', 'Q', ' '):
                                break
                    elif rec.EventType == 2:  # MOUSE_EVENT
                        mouse = rec.Event.MouseEvent
                        is_pressed = bool((mouse.dwButtonState & 0x0001) or (mouse.dwButtonState & 0x0002))
                        now = time.time()
                        if is_pressed and not prev_button_state and (now - last_click_time > 0.4):
                            last_click_time = now
                            start_time = now
                            click_x = mouse.dwMousePosition.X
                            click_y = mouse.dwMousePosition.Y

                            if prompt_y >= 0 and click_y == prompt_y:
                                if click_x < 26:
                                    _open_url_safely(repo_url, "GitHub Repo")
                                elif click_x < 52:
                                    _open_url_safely(sponsor_url, "Sponsor Dashboard")
                                else:
                                    break  # [Enter to exit] was clicked
                            elif prompt_y >= 0 and click_y in (prompt_y - 2, prompt_y - 3):
                                _open_url_safely(sponsor_url, "Sponsor Dashboard")
                            elif prompt_y >= 0 and click_y in (prompt_y - 4, prompt_y - 5):
                                _open_url_safely(repo_url, "GitHub Repo")
                            else:
                                if 26 <= click_x < 52:
                                    _open_url_safely(sponsor_url, "Sponsor Dashboard")
                                else:
                                    _open_url_safely(repo_url, "GitHub Repo")
                        prev_button_state = is_pressed
    finally:
        if hConIn and hConIn != -1 and orig_mode.value:
            kernel32.SetConsoleMode(hConIn, orig_mode.value)
            kernel32.CloseHandle(hConIn)
        if hConOut and hConOut != -1:
            kernel32.CloseHandle(hConOut)


def _run_posix_interactive_loop(repo_url: str, sponsor_url: str):
    """POSIX console event loop using select on stdin."""
    import select
    start_time = time.time()
    while time.time() - start_time < 30.0:
        r, _, _ = select.select([sys.stdin], [], [], 30.0)
        if r:
            line = sys.stdin.readline().strip().lower()
            if line in ("1", "s", "repo"):
                start_time = time.time()
                _open_url_safely(repo_url, "GitHub Repo")
            elif line in ("2", "c", "sponsor", "coffee"):
                start_time = time.time()
                _open_url_safely(sponsor_url, "Sponsor Dashboard")
            else:
                break
        else:
            break
