from pathlib import Path

from .errors import ManifestError
from .manifest import PetManifest


SUPPORTED_SCHEMA_VERSIONS = {1}
VALID_PLAYBACK_MODES = {"once", "loop", "pingpong"}


def _resolve_asset(root: Path, relative_path: Path) -> Path:
    """Resolve an asset while preventing absolute paths and package escapes."""
    if relative_path.is_absolute():
        raise ManifestError(f"Asset paths must be relative: {relative_path}")

    root_resolved = root.resolve()
    asset_resolved = (root_resolved / relative_path).resolve()
    try:
        asset_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ManifestError(
            f"Asset path must stay inside the pet package: {relative_path}"
        ) from exc
    return asset_resolved


def validate_manifest(manifest: PetManifest, *, check_assets: bool = True) -> None:
    """Validate manifest semantics independently from TOML parsing.

    Parsing answers "can this text become structured data?" Validation answers
    "is this a safe, internally consistent Deskling pet?" Keeping those jobs
    separate lets the same validation rules be reused by a future web builder,
    package importer, or other manifest source.
    """
    if manifest.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ManifestError(
            f"Unsupported schema_version {manifest.schema_version}; "
            f"supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    pet = manifest.pet
    if not pet.name.strip():
        raise ManifestError("Pet name cannot be empty")
    if pet.width <= 0 or pet.height <= 0 or pet.scale <= 0:
        raise ManifestError("Pet width, height, and scale must be greater than zero")
    if not pet.default_state.strip():
        raise ManifestError("Pet default_state cannot be empty")
    if not pet.default_animation.strip():
        raise ManifestError("Pet default_animation cannot be empty")

    if not manifest.animations:
        raise ManifestError("A pet must define at least one animation")

    for key, animation in manifest.animations.items():
        if not key.strip() or not animation.name.strip():
            raise ManifestError("Animation names cannot be empty")
        if key != animation.name:
            raise ManifestError(
                f"Animation key {key!r} does not match animation name {animation.name!r}"
            )
        if animation.mode not in VALID_PLAYBACK_MODES:
            raise ManifestError(
                f"Animation {animation.name!r} has invalid mode {animation.mode!r}"
            )
        if not animation.frames:
            raise ManifestError(
                f"Animation {animation.name!r} must define at least one frame"
            )

        for frame in animation.frames:
            if frame.duration_ms <= 0:
                raise ManifestError(
                    f"Animation {animation.name!r} has a frame with non-positive duration"
                )
            asset_path = _resolve_asset(manifest.root, frame.file)
            if check_assets and not asset_path.is_file():
                raise ManifestError(
                    f"Missing asset for {animation.name!r}: {asset_path}"
                )

    if pet.default_animation not in manifest.animations:
        raise ManifestError(
            f"Default animation {pet.default_animation!r} is not defined in [animations]"
        )

    for state, targets in manifest.transitions.items():
        if not state.strip():
            raise ManifestError("Transition state names cannot be empty")
        if any(not target.strip() for target in targets):
            raise ManifestError(f"State {state!r} contains an empty transition target")

    interaction = manifest.interaction
    if interaction is not None:
        for label, animation_name in (
            ("click_animation", interaction.click_animation),
            ("double_click_animation", interaction.double_click_animation),
        ):
            if animation_name is None:
                continue
            if not animation_name.strip():
                raise ManifestError(f"[interaction].{label} cannot be empty")
            if animation_name not in manifest.animations:
                raise ManifestError(
                    f"Interaction animation {animation_name!r} is not defined in [animations]"
                )

    idle = manifest.idle_behavior
    if idle is not None:
        if idle.min_delay_ms < 0 or idle.max_delay_ms < idle.min_delay_ms:
            raise ManifestError("[behavior.idle] has an invalid delay range")
        if not idle.actions:
            raise ManifestError("[behavior.idle] must define at least one action")
        for action in idle.actions:
            if not action.name.strip():
                raise ManifestError("Idle behavior action names cannot be empty")
            if action.weight <= 0:
                raise ManifestError("Idle behavior action weights must be greater than zero")
            if action.name not in manifest.animations:
                raise ManifestError(
                    f"Idle behavior action {action.name!r} is not defined in [animations]"
                )

    roam = manifest.roam_behavior
    if roam is not None:
        if roam.min_delay_ms < 0 or roam.max_delay_ms < roam.min_delay_ms:
            raise ManifestError("[behavior.roam] has an invalid delay range")
        if roam.min_walk_ms <= 0 or roam.max_walk_ms < roam.min_walk_ms:
            raise ManifestError("[behavior.roam] has an invalid walk duration range")
        if roam.speed_px_s <= 0:
            raise ManifestError("[behavior.roam].speed_px_s must be greater than zero")
        for animation_name in (roam.left_animation, roam.right_animation):
            if animation_name not in manifest.animations:
                raise ManifestError(
                    f"Roam animation {animation_name!r} is not defined in [animations]"
                )
