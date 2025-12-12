"""
Progress bar utilities for CLI.

Uses only stdlib - no external dependencies.
"""

import sys
import time
from typing import Optional, Iterator, TypeVar, Iterable


T = TypeVar('T')


class ProgressBar:
    """
    Simple progress bar for terminal output.

    Works without external dependencies, using only stdlib.
    """

    def __init__(
        self,
        total: int,
        description: str = "",
        width: int = 40,
        show_count: bool = True,
        show_percent: bool = True,
        show_eta: bool = True,
        file=None,
    ):
        """
        Initialize progress bar.

        Args:
            total: Total number of items
            description: Description text
            width: Bar width in characters
            show_count: Show count (e.g., "50/100")
            show_percent: Show percentage
            show_eta: Show estimated time remaining
            file: Output file (default: stderr)
        """
        self.total = total
        self.description = description
        self.width = width
        self.show_count = show_count
        self.show_percent = show_percent
        self.show_eta = show_eta
        self.file = file or sys.stderr

        self.current = 0
        self.start_time = None
        self._last_update = 0

    def start(self) -> None:
        """Start the progress bar."""
        self.start_time = time.time()
        self.current = 0
        self._render()

    def update(self, n: int = 1) -> None:
        """
        Update progress.

        Args:
            n: Number of items completed
        """
        self.current += n

        # Throttle updates to avoid excessive rendering
        now = time.time()
        if now - self._last_update < 0.1 and self.current < self.total:
            return

        self._last_update = now
        self._render()

    def set(self, n: int) -> None:
        """
        Set progress to specific value.

        Args:
            n: Current progress value
        """
        self.current = n
        self._render()

    def finish(self) -> None:
        """Complete the progress bar."""
        self.current = self.total
        self._render()
        print(file=self.file)  # New line

    def _render(self) -> None:
        """Render the progress bar."""
        if self.total == 0:
            percent = 100
        else:
            percent = (self.current / self.total) * 100

        filled = int(self.width * self.current / max(1, self.total))
        bar = "█" * filled + "░" * (self.width - filled)

        parts = []

        if self.description:
            parts.append(self.description)

        parts.append(f"|{bar}|")

        if self.show_percent:
            parts.append(f"{percent:5.1f}%")

        if self.show_count:
            parts.append(f"[{self.current}/{self.total}]")

        if self.show_eta and self.start_time and self.current > 0:
            elapsed = time.time() - self.start_time
            if self.current < self.total:
                eta = (elapsed / self.current) * (self.total - self.current)
                parts.append(f"ETA: {self._format_time(eta)}")
            else:
                parts.append(f"Time: {self._format_time(elapsed)}")

        line = " ".join(parts)

        # Clear line and write
        print(f"\r{line}", end="", file=self.file, flush=True)

    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m{secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h{minutes}m"

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.current < self.total:
            self.finish()


def progress(
    iterable: Iterable[T],
    total: Optional[int] = None,
    description: str = "",
    **kwargs,
) -> Iterator[T]:
    """
    Wrap an iterable with a progress bar.

    Args:
        iterable: Iterable to wrap
        total: Total count (auto-detected if possible)
        description: Description text
        **kwargs: Additional ProgressBar arguments

    Yields:
        Items from the iterable
    """
    if total is None:
        try:
            total = len(iterable)  # type: ignore
        except TypeError:
            # Can't determine length, convert to list
            iterable = list(iterable)
            total = len(iterable)

    bar = ProgressBar(total, description, **kwargs)
    bar.start()

    try:
        for item in iterable:
            yield item
            bar.update()
    finally:
        bar.finish()


class Spinner:
    """
    Simple spinner for indeterminate progress.
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    # Fallback for terminals that don't support unicode
    FRAMES_ASCII = ["|", "/", "-", "\\"]

    def __init__(
        self,
        description: str = "",
        use_unicode: bool = True,
        file=None,
    ):
        """
        Initialize spinner.

        Args:
            description: Description text
            use_unicode: Use unicode spinner frames
            file: Output file
        """
        self.description = description
        self.frames = self.FRAMES if use_unicode else self.FRAMES_ASCII
        self.file = file or sys.stderr

        self._frame_idx = 0
        self._running = False

    def spin(self) -> None:
        """Show next spinner frame."""
        frame = self.frames[self._frame_idx]
        self._frame_idx = (self._frame_idx + 1) % len(self.frames)

        text = f"\r{frame} {self.description}" if self.description else f"\r{frame}"
        print(text, end="", file=self.file, flush=True)

    def stop(self, message: str = "") -> None:
        """
        Stop the spinner.

        Args:
            message: Final message to display
        """
        if message:
            print(f"\r✓ {message}", file=self.file)
        else:
            print(f"\r✓ {self.description}", file=self.file)


class MultiProgress:
    """
    Manage multiple progress bars.
    """

    def __init__(self, file=None):
        """
        Initialize multi-progress manager.

        Args:
            file: Output file
        """
        self.file = file or sys.stderr
        self._bars: dict[str, ProgressBar] = {}

    def add(
        self,
        name: str,
        total: int,
        description: str = "",
        **kwargs,
    ) -> ProgressBar:
        """
        Add a progress bar.

        Args:
            name: Unique name for the bar
            total: Total items
            description: Description
            **kwargs: ProgressBar arguments

        Returns:
            The created ProgressBar
        """
        bar = ProgressBar(total, description or name, file=self.file, **kwargs)
        self._bars[name] = bar
        return bar

    def update(self, name: str, n: int = 1) -> None:
        """Update a specific bar."""
        if name in self._bars:
            self._bars[name].update(n)

    def finish(self, name: str) -> None:
        """Finish a specific bar."""
        if name in self._bars:
            self._bars[name].finish()

    def finish_all(self) -> None:
        """Finish all bars."""
        for bar in self._bars.values():
            bar.finish()
