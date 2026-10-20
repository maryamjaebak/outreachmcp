from __future__ import annotations

import os
from pathlib import Path

SOCIETY_DIR = os.environ.get("SOCIETY_DIR", "./society")
SOCIETY_EXAMPLE_DIR = os.environ.get("SOCIETY_EXAMPLE_DIR", "./society.example")

SECTIONS = ("profile", "past-events", "past-sponsors", "sponsorship-pack", "style")


class UnknownSectionError(Exception):
    pass


def _validate_section(section: str) -> None:
    if section not in SECTIONS:
        raise UnknownSectionError(
            f"unknown society section: {section!r}, must be one of {SECTIONS}"
        )


def read_section(section: str) -> str:
    """Read a society knowledge section, falling back to the shipped example.

    `society/` is gitignored (real, possibly private society data); on a
    fresh checkout it doesn't exist yet, so this falls back to the matching
    file in the committed `society.example/` until `update_society_info` or
    the user populates the real one.
    """
    _validate_section(section)
    real_path = Path(SOCIETY_DIR) / f"{section}.md"
    if real_path.exists():
        return real_path.read_text()
    example_path = Path(SOCIETY_EXAMPLE_DIR) / f"{section}.md"
    if example_path.exists():
        return example_path.read_text()
    raise FileNotFoundError(f"no content found for society section {section!r}")


def update_society_info(section: str, text: str) -> None:
    """Append a fact to a society knowledge section, creating `society/` as needed.

    The first time a section is written, it's seeded from the shipped
    example file (if any) so existing headings/structure aren't lost.
    """
    _validate_section(section)
    real_path = Path(SOCIETY_DIR) / f"{section}.md"
    real_path.parent.mkdir(parents=True, exist_ok=True)

    if not real_path.exists():
        example_path = Path(SOCIETY_EXAMPLE_DIR) / f"{section}.md"
        seed = example_path.read_text() if example_path.exists() else ""
        real_path.write_text(seed)

    with real_path.open("a") as f:
        f.write(f"\n{text.strip()}\n")
