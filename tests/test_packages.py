from pathlib import Path
import zipfile

import pytest

from desktoppet import ManifestError, NullBackend, Pet, load_manifest, pack_pet


BOO = Path(__file__).parents[1] / "examples" / "boo"


def test_boo_pack_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    package = pack_pet(BOO, tmp_path / "boo.deskling")

    assert package.is_file()
    with zipfile.ZipFile(package, "r") as archive:
        assert set(archive.namelist()) == {
            "pet.toml",
            "sprites/blink.svg",
            "sprites/idle_01.svg",
            "sprites/idle_02.svg",
            "sprites/spook.svg",
        }

    manifest = load_manifest(package)
    assert manifest.pet.name == "Boo"
    assert manifest.root != BOO
    assert manifest.root.is_dir()

    backend = NullBackend()
    pet = Pet(manifest, backend)
    assert backend.last_frame is not None
    assert backend.last_frame.name == "idle_01.svg"

    pet.handle_click(2)
    assert backend.last_frame is not None
    assert backend.last_frame.name == "spook.svg"


def test_package_output_is_deterministic(tmp_path: Path) -> None:
    first = pack_pet(BOO, tmp_path / "first.deskling")
    second = pack_pet(BOO, tmp_path / "second.deskling")
    assert first.read_bytes() == second.read_bytes()


def test_package_rejects_path_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    package = tmp_path / "unsafe.deskling"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("pet.toml", "schema_version = 1\n")
        archive.writestr("../escape.txt", "nope")

    with pytest.raises(ManifestError, match="escapes its root"):
        load_manifest(package)
    assert not (tmp_path / "escape.txt").exists()


def test_package_requires_root_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    package = tmp_path / "missing-manifest.deskling"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("nested/pet.toml", "schema_version = 1\n")

    with pytest.raises(ManifestError, match="exactly one root pet.toml"):
        load_manifest(package)
