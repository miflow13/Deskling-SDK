from __future__ import annotations

from .manifest import PetManifest


def _toml_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return format(value, ".12g")


def manifest_to_toml(manifest: PetManifest) -> str:
    """Serialize a validated declarative manifest as Pet Format v1 TOML.

    The writer intentionally works only with config dataclasses. GUI tools,
    future web builders, and command-line utilities can therefore round-trip a
    pet without depending on runtime animation or platform objects.
    """
    pet = manifest.pet
    lines = [
        f"schema_version = {manifest.schema_version}",
        "",
        "[pet]",
        f"name = {_toml_string(pet.name)}",
        f"width = {pet.width}",
        f"height = {pet.height}",
        f"scale = {_number(pet.scale)}",
        f"default_state = {_toml_string(pet.default_state)}",
        f"default_animation = {_toml_string(pet.default_animation)}",
    ]

    for name, animation in manifest.animations.items():
        lines.extend(
            [
                "",
                f"[animations.{name}]",
                f"mode = {_toml_string(animation.mode)}",
                "frames = [",
            ]
        )
        for frame in animation.frames:
            lines.append(
                "  { file = "
                f"{_toml_string(frame.file.as_posix())}, "
                f"duration_ms = {frame.duration_ms} }},"
            )
        lines.append("]")

    interaction = manifest.interaction
    if interaction is not None:
        lines.extend(["", "[interaction]"])
        if interaction.click_animation is not None:
            lines.append(
                f"click_animation = {_toml_string(interaction.click_animation)}"
            )
        if interaction.double_click_animation is not None:
            lines.append(
                "double_click_animation = "
                f"{_toml_string(interaction.double_click_animation)}"
            )

    if manifest.transitions:
        lines.extend(["", "[transitions]"])
        for state, targets in manifest.transitions.items():
            rendered_targets = ", ".join(
                _toml_string(target) for target in sorted(targets)
            )
            lines.append(f"{state} = [{rendered_targets}]")

    idle = manifest.idle_behavior
    if idle is not None:
        lines.extend(
            [
                "",
                "[behavior.idle]",
                f"min_delay_ms = {idle.min_delay_ms}",
                f"max_delay_ms = {idle.max_delay_ms}",
                "actions = [",
            ]
        )
        for action in idle.actions:
            lines.append(
                "  { name = "
                f"{_toml_string(action.name)}, weight = {_number(action.weight)} }},"
            )
        lines.append("]")

    roam = manifest.roam_behavior
    if roam is not None:
        lines.extend(
            [
                "",
                "[behavior.roam]",
                f"min_delay_ms = {roam.min_delay_ms}",
                f"max_delay_ms = {roam.max_delay_ms}",
                f"min_walk_ms = {roam.min_walk_ms}",
                f"max_walk_ms = {roam.max_walk_ms}",
                f"speed_px_s = {_number(roam.speed_px_s)}",
                f"left_animation = {_toml_string(roam.left_animation)}",
                f"right_animation = {_toml_string(roam.right_animation)}",
            ]
        )

    return "\n".join(lines) + "\n"
