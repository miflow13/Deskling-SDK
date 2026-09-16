from desktoppet.animation import Animation, Frame, PlaybackMode
from desktoppet.behavior import BehaviorAction
from desktoppet.config.manifest import BehaviorConfig, PetManifest


def build_animations(manifest: PetManifest) -> dict[str, Animation]:
    """Convert declarative animation config into runtime animation objects."""
    animations: dict[str, Animation] = {}
    for name, config in manifest.animations.items():
        frames = [
            Frame(manifest.root / frame.file, frame.duration_ms)
            for frame in config.frames
        ]
        animations[name] = Animation(
            name=config.name,
            frames=frames,
            mode=PlaybackMode(config.mode),
        )
    return animations


def build_behavior_actions(config: BehaviorConfig) -> list[BehaviorAction]:
    """Convert declarative idle-action config into scheduler runtime objects."""
    return [
        BehaviorAction(name=action.name, weight=action.weight)
        for action in config.actions
    ]
