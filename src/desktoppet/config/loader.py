from pathlib import Path
import tomllib

from desktoppet.animation import Animation, Frame, PlaybackMode
from desktoppet.behavior import BehaviorAction

from .manifest import BehaviorConfig, PetManifest, PetSettings, RoamConfig


class ManifestError(ValueError):
    pass


def load_manifest(path: str | Path, *, check_assets: bool = True) -> PetManifest:
    """Translate a human-written pet.toml into validated Python objects.

    Learning note:
        pet.toml is only a description of a pet. The loader is the front door of
        the SDK: it reads that text, turns it into dictionaries, validates it,
        and finally returns a PetManifest that the engine can work with.

        pet.toml -> tomllib -> dicts -> dataclasses -> PetManifest
    """
    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / "pet.toml"
    if not manifest_path.exists():
        raise ManifestError(f"Manifest not found: {manifest_path}")

    try:
        # Step 1: read_text() loads pet.toml from disk as one Python string.
        # Step 2: tomllib.loads() parses that TOML string into nested dictionaries.
        # Example: [pet] name = "Slime" becomes roughly
        # {"pet": {"name": "Slime"}}.
        data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"Could not read manifest: {exc}") from exc

    root = manifest_path.parent

    # data.get("pet", {}) pulls just the [pet] table out of the parsed TOML.
    # The empty dict is a safe fallback; required fields are validated below.
    pet_data = data.get("pet", {})
    try:
        # Convert loose dictionary values into a strongly structured PetSettings
        # object. From here onward, engine code can use pet.name / pet.width etc.
        # instead of repeatedly indexing raw dictionaries.
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

    if pet.width <= 0 or pet.height <= 0 or pet.scale <= 0:
        raise ManifestError("Pet width, height, and scale must be greater than zero")

    # Each [animations.*] TOML table becomes an Animation object containing
    # Frame objects. Notice that the loader creates animation DATA; it does not
    # decide when or why an animation should play.
    animations: dict[str, Animation] = {}
    for name, animation_data in data.get("animations", {}).items():
        try:
            mode = PlaybackMode(str(animation_data.get("mode", "loop")))
            frames = []
            for frame_data in animation_data["frames"]:
                frame_path = root / str(frame_data["file"])
                if check_assets and not frame_path.exists():
                    raise ManifestError(f"Missing asset for {name!r}: {frame_path}")
                frames.append(Frame(frame_path, int(frame_data["duration_ms"])))
            animations[name] = Animation(name=name, frames=frames, mode=mode)
        except ManifestError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError(f"Invalid animation {name!r}: {exc}") from exc

    if pet.default_animation not in animations:
        raise ManifestError(
            f"Default animation {pet.default_animation!r} is not defined in [animations]"
        )

    transitions = {
        str(state): {str(target) for target in targets}
        for state, targets in data.get("transitions", {}).items()
    }

    behavior_data = data.get("behavior", {})

    idle_behavior = None
    idle_data = behavior_data.get("idle")
    if idle_data:
        try:
            idle_behavior = BehaviorConfig(
                min_delay_ms=int(idle_data.get("min_delay_ms", 5000)),
                max_delay_ms=int(idle_data.get("max_delay_ms", 15000)),
                actions=[
                    BehaviorAction(str(action["name"]), float(action.get("weight", 1.0)))
                    for action in idle_data.get("actions", [])
                ],
            )
            if not idle_behavior.actions:
                raise ManifestError("[behavior.idle] must define at least one action")
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ManifestError):
                raise
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
            if roam_behavior.min_delay_ms < 0 or roam_behavior.max_delay_ms < roam_behavior.min_delay_ms:
                raise ManifestError("[behavior.roam] has an invalid delay range")
            if roam_behavior.min_walk_ms <= 0 or roam_behavior.max_walk_ms < roam_behavior.min_walk_ms:
                raise ManifestError("[behavior.roam] has an invalid walk duration range")
            if roam_behavior.speed_px_s <= 0:
                raise ManifestError("[behavior.roam].speed_px_s must be greater than zero")
            for animation_name in (
                roam_behavior.left_animation,
                roam_behavior.right_animation,
            ):
                if animation_name not in animations:
                    raise ManifestError(
                        f"Roam animation {animation_name!r} is not defined in [animations]"
                    )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ManifestError):
                raise
            raise ManifestError(f"Invalid [behavior.roam] section: {exc}") from exc

    # PetManifest is the finished, validated blueprint handed to the Pet engine.
    # After this point the core does not need to know anything about TOML parsing.
    return PetManifest(
        root=root,
        pet=pet,
        animations=animations,
        transitions=transitions,
        idle_behavior=idle_behavior,
        roam_behavior=roam_behavior,
    )
