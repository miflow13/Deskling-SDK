from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


PACKAGE_SUFFIX = ".deskling"
MAX_PACKAGE_FILES = 1000
MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 10 * 1024 * 1024


class PackageError(ValueError):
    """Raised when a .deskling package is malformed or unsafe."""


def _cache_root() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache else Path.home() / ".cache"
    return base / "deskling" / "packages"


def _safe_member_path(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename
    if not name or "\\" in name:
        raise PackageError(f"Invalid package path: {name!r}")

    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise PackageError(f"Package entry escapes its root: {name!r}")

    # ZIP archives can carry Unix file-type bits. Never materialize symlinks or
    # special files from downloaded pets; Deskling packages are data-only.
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise PackageError(f"Unsupported package entry type: {name!r}")
    if info.flag_bits & 0x1:
        raise PackageError(f"Encrypted package entries are not supported: {name!r}")
    return path


def _inspect_archive(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, PurePosixPath]]:
    infos = archive.infolist()
    if len(infos) > MAX_PACKAGE_FILES:
        raise PackageError(
            f"Package contains too many entries ({len(infos)} > {MAX_PACKAGE_FILES})"
        )

    total_bytes = 0
    seen: set[PurePosixPath] = set()
    members: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    for info in infos:
        path = _safe_member_path(info)
        if path in seen:
            raise PackageError(f"Duplicate package entry: {info.filename!r}")
        seen.add(path)

        if info.file_size > MAX_FILE_BYTES:
            raise PackageError(
                f"Package entry is too large: {info.filename!r} ({info.file_size} bytes)"
            )
        total_bytes += info.file_size
        if total_bytes > MAX_PACKAGE_BYTES:
            raise PackageError(
                f"Package expands beyond {MAX_PACKAGE_BYTES} bytes"
            )
        members.append((info, path))

    manifest_path = PurePosixPath("pet.toml")
    manifest_entries = [info for info, path in members if path == manifest_path and not info.is_dir()]
    if len(manifest_entries) != 1:
        raise PackageError("A .deskling package must contain exactly one root pet.toml")
    return members


def materialize_package(path: str | Path) -> Path:
    """Safely materialize a .deskling archive into a content-addressed cache."""
    package_path = Path(path)
    if package_path.suffix.lower() != PACKAGE_SUFFIX:
        raise PackageError(f"Not a {PACKAGE_SUFFIX} package: {package_path}")
    if not package_path.is_file():
        raise PackageError(f"Package not found: {package_path}")

    try:
        digest = hashlib.sha256(package_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise PackageError(f"Could not read package: {exc}") from exc

    cache_root = _cache_root()
    target = cache_root / digest
    if (target / "pet.toml").is_file():
        return target

    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(package_path, "r") as archive:
            members = _inspect_archive(archive)
            temp_dir = Path(tempfile.mkdtemp(prefix=f".{digest}-", dir=cache_root))
            try:
                for info, member_path in members:
                    destination = temp_dir.joinpath(*member_path.parts)
                    if info.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info, "r") as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)

                if target.exists():
                    shutil.rmtree(target)
                os.replace(temp_dir, target)
            except Exception:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise
    except PackageError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise PackageError(f"Could not open package: {exc}") from exc

    return target


def resolve_project_path(path: str | Path) -> Path:
    """Return a normal project path for either a folder/pet.toml or .deskling."""
    source = Path(path)
    if source.suffix.lower() == PACKAGE_SUFFIX:
        return materialize_package(source)
    return source


def _deterministic_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def pack_pet(project: str | Path, output: str | Path | None = None) -> Path:
    """Build a deterministic data-only .deskling package from a pet project."""
    project_path = Path(project)
    if project_path.is_file() and project_path.name == "pet.toml":
        project_path = project_path.parent
    if not project_path.is_dir():
        raise PackageError(f"Pet project not found: {project_path}")

    # Local import avoids coupling config parsing to archive mechanics while still
    # requiring the source project to pass the same validation users get at run time.
    from desktoppet.config.loader import load_manifest

    manifest = load_manifest(project_path)
    manifest_file = project_path / "pet.toml"

    asset_paths: set[Path] = set()
    for animation in manifest.animations.values():
        for frame in animation.frames:
            asset_paths.add(frame.file)

    destination = Path(output) if output is not None else project_path.with_suffix(PACKAGE_SUFFIX)
    if destination.suffix.lower() != PACKAGE_SUFFIX:
        destination = destination.with_suffix(PACKAGE_SUFFIX)
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(destination, "w") as archive:
            archive.writestr(_deterministic_info("pet.toml"), manifest_file.read_bytes())
            for relative_path in sorted(asset_paths, key=lambda item: item.as_posix()):
                source = manifest.root / relative_path
                archive.writestr(
                    _deterministic_info(relative_path.as_posix()),
                    source.read_bytes(),
                )
    except OSError as exc:
        raise PackageError(f"Could not write package: {exc}") from exc

    return destination
