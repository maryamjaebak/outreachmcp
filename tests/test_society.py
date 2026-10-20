from pathlib import Path

import pytest

from outreach_mcp import society


@pytest.fixture(autouse=True)
def _isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(society, "SOCIETY_DIR", str(tmp_path / "society"))
    monkeypatch.setattr(society, "SOCIETY_EXAMPLE_DIR", str(tmp_path / "society.example"))


def test_rejects_unknown_section() -> None:
    with pytest.raises(society.UnknownSectionError):
        society.read_section("not-a-real-section")


def test_read_section_falls_back_to_example(tmp_path: Path) -> None:
    example_dir = tmp_path / "society.example"
    example_dir.mkdir()
    (example_dir / "profile.md").write_text("Example profile text")

    assert society.read_section("profile") == "Example profile text"


def test_read_section_prefers_real_over_example(tmp_path: Path) -> None:
    example_dir = tmp_path / "society.example"
    example_dir.mkdir()
    (example_dir / "profile.md").write_text("Example profile text")

    real_dir = tmp_path / "society"
    real_dir.mkdir()
    (real_dir / "profile.md").write_text("Real profile text")

    assert society.read_section("profile") == "Real profile text"


def test_read_section_raises_when_neither_exists() -> None:
    with pytest.raises(FileNotFoundError):
        society.read_section("profile")


def test_update_society_info_creates_real_file_from_example(tmp_path: Path) -> None:
    example_dir = tmp_path / "society.example"
    example_dir.mkdir()
    (example_dir / "profile.md").write_text("# Society Profile\n")

    society.update_society_info("profile", "We won the regional hackathon.")

    content = society.read_section("profile")
    assert "# Society Profile" in content
    assert "We won the regional hackathon." in content


def test_update_society_info_appends_on_repeat_calls() -> None:
    society.update_society_info("past-sponsors", "Acme Corp, Gold, 2026")
    society.update_society_info("past-sponsors", "Beta Ltd, Silver, 2026")

    content = society.read_section("past-sponsors")
    assert "Acme Corp, Gold, 2026" in content
    assert "Beta Ltd, Silver, 2026" in content


def test_update_society_info_rejects_unknown_section() -> None:
    with pytest.raises(society.UnknownSectionError):
        society.update_society_info("not-a-real-section", "text")
