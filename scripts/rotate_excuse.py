#!/usr/bin/env python3
"""Rotate the 'Excuse of the Day' block in README.md."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

START_MARKER = "<!-- EXCUSE_OF_THE_DAY:START -->"
END_MARKER = "<!-- EXCUSE_OF_THE_DAY:END -->"
MAX_EXCUSES = 500
MAX_README_BYTES = 1_048_576


def load_excuses(path: Path) -> list[str]:
    """Load and validate the curated excuse list from a JSON file."""
    assert isinstance(path, Path), "path must be a Path instance"
    assert path.suffix == ".json", "excuses file must have a .json extension"

    if not path.is_file():
        raise FileNotFoundError(f"Excuses file not found: {path}")

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, list):
        raise ValueError("Excuses JSON root must be a list of strings")

    excuses: list[str] = []
    for index, entry in enumerate(raw_data):
        if index >= MAX_EXCUSES:
            raise ValueError(f"Excuses list exceeds safety bound of {MAX_EXCUSES}")
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError(f"Invalid excuse at index {index}: must be non-empty string")
        excuses.append(entry.strip())

    assert len(excuses) >= 2, "At least two excuses are required to guarantee rotation"
    return excuses


def extract_current_excuse(readme_text: str) -> tuple[int, int, str]:
    """Return marker content span (start_idx, end_idx) and current excuse text."""
    assert isinstance(readme_text, str), "readme_text must be a string"
    assert len(readme_text) <= MAX_README_BYTES, "README exceeds maximum size bound"

    start_pos = readme_text.find(START_MARKER)
    end_pos = readme_text.find(END_MARKER)
    if start_pos < 0 or end_pos < 0 or end_pos <= start_pos:
        raise ValueError("Valid EXCUSE_OF_THE_DAY start/end markers not found in README")

    content_start = start_pos + len(START_MARKER)
    current_block = readme_text[content_start:end_pos].strip()
    cleaned = current_block.lstrip("> ").strip().strip('*').strip('"')

    assert content_start <= end_pos, "Content span must be non-negative"
    return content_start, end_pos, cleaned


def pick_next_excuse(excuses: list[str], current_excuse: str) -> str:
    """Select a new excuse different from current_excuse using secure randomness."""
    assert len(excuses) >= 2, "At least two excuses required"
    assert isinstance(current_excuse, str), "current_excuse must be a string"

    candidates = [item for item in excuses if item != current_excuse]
    if not candidates:
        raise ValueError("No alternative excuse available to rotate to")

    chosen = secrets.choice(candidates)
    assert chosen != current_excuse, "Chosen excuse must differ from current excuse"
    return chosen


def render_updated_readme(
    readme_text: str,
    content_start: int,
    end_pos: int,
    new_excuse: str,
) -> str:
    """Splice the formatted excuse into the README between the markers."""
    assert 0 <= content_start <= end_pos <= len(readme_text), "Invalid slice bounds"
    assert bool(new_excuse.strip()), "new_excuse must be non-empty"

    formatted_block = f'\n> *"{new_excuse}"*\n> '
    updated = readme_text[:content_start] + formatted_block + readme_text[end_pos:]

    assert START_MARKER in updated and END_MARKER in updated, "Markers must be preserved"
    return updated


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    assert isinstance(argv, list), "argv must be a list"

    parser = argparse.ArgumentParser(description="Rotate README Excuse of the Day.")
    parser.add_argument(
        "--readme",
        type=Path,
        default=Path("README.md"),
        help="Path to README.md",
    )
    parser.add_argument(
        "--excuses",
        type=Path,
        default=Path("data/excuses.json"),
        help="Path to excuses JSON file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected excuse without modifying README.md",
    )
    parsed = parser.parse_args(argv)
    assert isinstance(parsed.readme, Path), "Parsed readme must be a Path"
    return parsed


def main(argv: list[str]) -> int:
    """Entry point with explicit error handling and return codes."""
    assert isinstance(argv, list), "argv must be a list"

    try:
        args = parse_args(argv)
        excuses = load_excuses(args.excuses)
        if not args.readme.is_file():
            raise FileNotFoundError(f"README file not found: {args.readme}")

        readme_text = args.readme.read_text(encoding="utf-8")
        content_start, end_pos, current = extract_current_excuse(readme_text)
        chosen = pick_next_excuse(excuses, current)
        updated = render_updated_readme(readme_text, content_start, end_pos, chosen)

        assert updated != readme_text, "Updated README must differ from original"
        if args.dry_run:
            print(f"[dry-run] Next excuse: {chosen}")
            return 0

        bytes_written = args.readme.write_text(updated, encoding="utf-8")
        assert bytes_written > 0, "Failed to write updated README"
        print(f"Rotated excuse to: {chosen}")
        return 0
    except (AssertionError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error rotating excuse: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
