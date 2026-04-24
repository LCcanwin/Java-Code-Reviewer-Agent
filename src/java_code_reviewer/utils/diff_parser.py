"""Diff parser utilities."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiffFile:
    """Represents a changed file in a diff."""

    old_path: str
    new_path: str
    hunks: list["DiffHunk"]


@dataclass
class DiffHunk:
    """Represents a hunk (contiguous change) in a diff."""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    lines: list[str]


class DiffParser:
    """Parse unified diff format."""

    @staticmethod
    def parse(diff_content: str) -> list[DiffFile]:
        """Parse diff content into structured DiffFile objects."""
        files: list[DiffFile] = []
        current_file: Optional[DiffFile] = None
        current_hunk: Optional[DiffHunk] = None

        for line in diff_content.split("\n"):
            if line.startswith("--- ") or line.startswith("diff "):
                if current_file is not None and current_hunk is not None:
                    files.append(current_file)

                old_path = DiffParser._parse_old_path(line)
                current_file = DiffFile(old_path=old_path, new_path="", hunks=[])
                current_hunk = None

            elif line.startswith("+++ "):
                if current_file is not None:
                    current_file.new_path = DiffParser._parse_new_path(line)

            elif line.startswith("@@ "):
                if current_file is not None and current_hunk is not None:
                    current_file.hunks.append(current_hunk)

                current_hunk = DiffParser._parse_hunk_header(line)

            elif current_hunk is not None:
                current_hunk.lines.append(line)

        if current_file is not None and current_hunk is not None:
            current_file.hunks.append(current_hunk)
            files.append(current_file)

        return files

    @staticmethod
    def _parse_old_path(line: str) -> str:
        """Parse old path from --- line."""
        match = re.match(r"--- (?:a/)?(.+)", line)
        return match.group(1) if match else ""

    @staticmethod
    def _parse_new_path(line: str) -> str:
        """Parse new path from +++ line."""
        match = re.match(r"\+\+\+ (?:b/)?(.+)", line)
        return match.group(1) if match else ""

    @staticmethod
    def _parse_hunk_header(line: str) -> DiffHunk:
        """Parse @@ header into hunk metadata."""
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if match:
            old_start = int(match.group(1))
            old_lines = int(match.group(2) or 1)
            new_start = int(match.group(3))
            new_lines = int(match.group(4) or 1)
            return DiffHunk(old_start, old_lines, new_start, new_lines, [])
        return DiffHunk(0, 0, 0, 0, [])

    @staticmethod
    def extract_changed_lines(diff_content: str) -> dict[str, list[int]]:
        """Extract line numbers for each changed file."""
        changed_lines: dict[str, list[int]] = {}
        files = DiffParser.parse(diff_content)

        for file in files:
            line_numbers: set[int] = set()
            for hunk in file.hunks:
                current_new_line = hunk.new_start
                for line in hunk.lines:
                    if line.startswith("+") or line.startswith("-"):
                        line_numbers.add(current_new_line)
                    if not line.startswith("-"):
                        current_new_line += 1

            if line_numbers:
                changed_lines[file.new_path or file.old_path] = sorted(line_numbers)

        return changed_lines
