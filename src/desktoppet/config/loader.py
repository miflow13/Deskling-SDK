from pathlib import Path
import tomllib
from typing import cast

from .errors import ManifestError
from .manifest import (
    AnimationConfig,
    BehaviorActionConfig,
    BehaviorConfig,
    FrameConfig,
    InteractionConfig,
    PetManifest,
    PetSettings,
    PlaybackModeName,
    RoamConfig,
)
from .validation import validate_manifest


def load_manifest(path: str | Path, *, check_assets: bool = True) -> PetManifest:
    """Parse pet.toml into declarative config, then validate that config.

    The loader intentionally stops at configuration data. Runtime objects are
    created later by desktoppet.runtime, which keeps TOML parsing independent
    from animation playback, behavior scheduling, and platform code.

        pet.toml -> loader -> PetManifest -> validation -> runtime builder -> Pet
    """
    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / "pet.toml"
    if not manifest_path.exists():
        raise ManifestError(f"Manifest not found: {manifest_path}")

    try:
        data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"Could not read manifest: {exc}") from exc

    root = manifest_path.parent.resolve()

    try:
        schema_version = int(data["schema_version"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ManifestError(f"Invalid schema_version: {exc}") from exc

    pet_data = data.get("pet", {})
    try:
        pet = PetSettings(
            name=str(pet_data["name"]),
            width=int(pet_data["width"]),
            height=int(pet_data["height"]),
            scale=float(pet_data.get("scale", 1.0)),
            default_state=str(pet_data.get("default_state", "idle")),
            default_animation=str(pet_data.get("default_animation", "idle")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ManifestError(f"Invalid [pet] section: {exc}") from exc

    animations: dict[str, AnimationConfig] = {}
    try:
        animation_tables = data.get("animations", {})
        for raw_name, animation_data in animation_tables.items():
            name = str(raw_name)
            mode = cast(
                PlaybackModeName,
                str(animation_data.get("mode", "loop")),
            )
            frames = tuple(
                FrameConfig(
                    file=Path(str(frame_data["file"])),
                    duration_ms=int(frame_data["duration_ms"]),
                )
                for frame_data in animation_data["frames"]
            )
            animations[name] = AnimationConfig(
                name=name,
                frames=frames,
                mode=mode,
            )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ManifestError(f"Invalid [animations] section: {exc}") from exc

    try:
        transitions = {
            str(state): {str(target) for target in targets}
            for state, targets in data.get("transitions", {}).items()
        }
    except (AttributeError, TypeError, ValueError) as exc:
        raise ManifestError(f"Invalid [transitions] section: {exc}") from exc

    interaction = None
    interaction_data = data.get("interaction")
    if interaction_data:
        try:
            click_value = interaction_data.get("click_animation")
            double_click_value = interaction_data.get("double_click_animation")
            interaction = InteractionConfig(
                click_animation=str(click_value) if click_value is not None else None,
                double_click_animation=(
                    str(double_click_value) if double_click_value is not None else None
                ),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise ManifestError(f"Invalid [interaction] section: {exc}") from exc

    behavior_data = data.get("behavior", {})

    idle_behavior = None
    idle_data = behavior_data.get("idle")
    if idle_data:
        try:
            idle_behavior = BehaviorConfig(
                min_delay_ms=int(idle_data.get("min_delay_ms", 5000)),
                max_delay_ms=int(idle_data.get("max_delay_ms", 15000)),
                actions=tuple(
                    BehaviorActionConfig(
                        name=str(action["name"]),
                        weight=float(action.get("weight", 1.0)),
                    )
                    for action in idle_data.get("actions", [])
                ),
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ManifestError(f"Invalid [behavior.idle] section: {exc}") from exc

    roam_behavior = None
    roam_data = behavior_data.get("roam")
    if roam_data:
        try:
            roam_behavior = RoamConfig(
                min_delay_ms=int(roam_data.get("min_delay_ms", 5000)),
                max_delay_ms=int(roam_data.get("max_delay_ms", 12000)),
                min_walk_ms=int(roam_data.get("min_walk_ms", 800)),
                max_walk_ms=int(roam_data.get("max_walk_ms", 2200)),
                speed_px_s=float(roam_data.get("speed_px_s", 80.0)),
                left_animation=str(roam_data.get("left_animation", "walk_left")),
                right_animation=str(roam_data.get("right_animation", "walk_right")),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise ManifestError(f"Invalid [behavior.roam] section: {exc}") from exc

    manifest = PetManifest(
        schema_version=schema_version,
        root=root,
        pet=pet,
        animations=animations,
        transitions=transitions,
        idle_behavior=idle_behavior,
        roam_behavior=roam_behavior,
        interaction=interaction,
    )
    validate_manifest(manifest, check_assets=check_assets)
    return manifest
