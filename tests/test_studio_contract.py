from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
STUDIO = ROOT / "studio"


def test_studio_is_static_and_client_only() -> None:
    html = (STUDIO / "index.html").read_text(encoding="utf-8")
    app = (STUDIO / "app.js").read_text(encoding="utf-8")

    assert 'src="./app.js"' in html
    assert 'href="./styles.css"' in html
    assert "https://" not in html
    assert "http://" not in html
    assert "fetch(" not in app
    assert "XMLHttpRequest" not in app


def test_studio_targets_pet_format_v1_and_root_manifest() -> None:
    app = (STUDIO / "app.js").read_text(encoding="utf-8")

    assert '"schema_version = 1"' in app
    assert '"[pet]"' in app
    assert 'name: "pet.toml"' in app
    assert "sprites/${animation.manifestName}_" in app
    assert 'default_animation = \\"idle\\"' not in app  # guard accidental double escaping
    assert 'default_animation = "idle"' in app


def test_studio_zip_writer_uses_standard_stored_zip_signatures() -> None:
    app = (STUDIO / "app.js").read_text(encoding="utf-8")

    assert "0x04034b50" in app  # local file header
    assert "0x02014b50" in app  # central directory header
    assert "0x06054b50" in app  # end of central directory
    assert "0x81a40000" in app  # regular Unix file, 0644
    assert "crc32" in app


def test_studio_javascript_parses_when_node_is_available() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed in this environment")

    result = subprocess.run(
        [node, "--check", str(STUDIO / "app.js")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
