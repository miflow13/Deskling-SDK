from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from desktoppet.config import (
    AnimationConfig,
    BehaviorActionConfig,
    BehaviorConfig,
    FrameConfig,
    InteractionConfig,
    PetManifest,
    PetSettings,
    validate_manifest,
)


BODY_CHOICES = ("blob", "round", "ghost")
EYE_CHOICES = ("dot", "sleepy", "sparkle")
MOUTH_CHOICES = ("smile", "cat", "tiny")
ACCESSORY_CHOICES = ("sprout", "bow", "glasses", "crown", "none")
PALETTE_CHOICES = ("mint", "pink", "lavender", "peach", "sky")

PALETTES = {
    "mint": {
        "main": "#A8E6CF",
        "shadow": "#73C8A4",
        "accent": "#FF83B4",
        "blush": "#F5A8B8",
    },
    "pink": {
        "main": "#F7B7D2",
        "shadow": "#E78EB6",
        "accent": "#8CCEF4",
        "blush": "#F687A9",
    },
    "lavender": {
        "main": "#C8B6FF",
        "shadow": "#9F8BE6",
        "accent": "#FFD166",
        "blush": "#F3A9C3",
    },
    "peach": {
        "main": "#FFCBA4",
        "shadow": "#EFA477",
        "accent": "#7BDCB5",
        "blush": "#F28E8E",
    },
    "sky": {
        "main": "#A9D6FF",
        "shadow": "#74B4EA",
        "accent": "#FF9FCB",
        "blush": "#F4A9B8",
    },
}

_OUTLINE = "#26332E"
_WHITE = "#FFFDF8"


@dataclass(frozen=True, slots=True)
class TemplateOptions:
    body: str = "blob"
    eyes: str = "dot"
    mouth: str = "smile"
    accessory: str = "sprout"
    palette: str = "mint"


def _validate_options(options: TemplateOptions) -> None:
    for value, choices, label in (
        (options.body, BODY_CHOICES, "body"),
        (options.eyes, EYE_CHOICES, "eyes"),
        (options.mouth, MOUTH_CHOICES, "mouth"),
        (options.accessory, ACCESSORY_CHOICES, "accessory"),
        (options.palette, PALETTE_CHOICES, "palette"),
    ):
        if value not in choices:
            raise ValueError(f"Unknown {label} template choice: {value}")


def _body_svg(body: str, main: str, shadow: str) -> str:
    if body == "blob":
        return f'''
        <path d="M28 83 C23 68 26 49 38 38 C49 27 76 24 91 36 C104 47 107 67 100 84 C94 99 82 105 64 105 C44 105 33 99 28 83 Z"
              fill="{main}" stroke="{_OUTLINE}" stroke-width="4" stroke-linejoin="round"/>
        <path d="M36 86 C43 97 84 102 94 84 C91 99 80 105 64 105 C46 105 35 99 30 87 Z"
              fill="{shadow}" opacity="0.42"/>
        <ellipse cx="47" cy="45" rx="10" ry="6" fill="{_WHITE}" opacity="0.28"/>
        '''
    if body == "round":
        return f'''
        <ellipse cx="64" cy="69" rx="39" ry="37"
                 fill="{main}" stroke="{_OUTLINE}" stroke-width="4"/>
        <path d="M31 81 C41 101 83 108 98 83 C92 101 79 106 64 106 C46 106 34 98 31 81 Z"
              fill="{shadow}" opacity="0.42"/>
        <ellipse cx="47" cy="47" rx="10" ry="6" fill="{_WHITE}" opacity="0.28"/>
        '''
    return f'''
    <path d="M28 96 V62 C28 40 43 27 64 27 C85 27 100 40 100 62 V96
             L91 88 L82 97 L73 88 L64 97 L55 88 L46 97 L37 88 Z"
          fill="{main}" stroke="{_OUTLINE}" stroke-width="4" stroke-linejoin="round"/>
    <path d="M31 81 V94 L37 87 L46 96 L55 87 L64 96 L73 87 L82 96 L91 87 L97 93 V82
             C89 99 42 101 31 81 Z" fill="{shadow}" opacity="0.38"/>
    <ellipse cx="46" cy="45" rx="9" ry="5" fill="{_WHITE}" opacity="0.28"/>
    '''


def _eyes_svg(eyes: str, *, closed: bool) -> str:
    if closed:
        return f'''
        <path d="M45 64 Q51 68 57 64" fill="none" stroke="{_OUTLINE}" stroke-width="4" stroke-linecap="round"/>
        <path d="M71 64 Q77 68 83 64" fill="none" stroke="{_OUTLINE}" stroke-width="4" stroke-linecap="round"/>
        '''
    if eyes == "dot":
        return f'''
        <circle cx="51" cy="63" r="4.5" fill="{_OUTLINE}"/>
        <circle cx="77" cy="63" r="4.5" fill="{_OUTLINE}"/>
        <circle cx="49.5" cy="61.5" r="1.2" fill="{_WHITE}"/>
        <circle cx="75.5" cy="61.5" r="1.2" fill="{_WHITE}"/>
        '''
    if eyes == "sleepy":
        return f'''
        <path d="M44 62 Q51 69 58 62" fill="none" stroke="{_OUTLINE}" stroke-width="4" stroke-linecap="round"/>
        <path d="M70 62 Q77 69 84 62" fill="none" stroke="{_OUTLINE}" stroke-width="4" stroke-linecap="round"/>
        '''
    return f'''
    <path d="M51 56 L53 61 L58 63 L53 65 L51 70 L49 65 L44 63 L49 61 Z" fill="{_OUTLINE}"/>
    <path d="M77 56 L79 61 L84 63 L79 65 L77 70 L75 65 L70 63 L75 61 Z" fill="{_OUTLINE}"/>
    <circle cx="50" cy="60" r="1.3" fill="{_WHITE}"/>
    <circle cx="76" cy="60" r="1.3" fill="{_WHITE}"/>
    '''


def _mouth_svg(mouth: str) -> str:
    if mouth == "smile":
        return f'<path d="M57 77 Q64 84 71 77" fill="none" stroke="{_OUTLINE}" stroke-width="3.5" stroke-linecap="round"/>'
    if mouth == "cat":
        return f'<path d="M55 77 Q60 83 64 77 Q68 83 73 77" fill="none" stroke="{_OUTLINE}" stroke-width="3.2" stroke-linecap="round"/>'
    return f'<ellipse cx="64" cy="78" rx="2.5" ry="3.3" fill="{_OUTLINE}"/>'


def _accessory_svg(accessory: str, accent: str) -> str:
    if accessory == "sprout":
        return f'''
        <path d="M64 31 Q64 21 64 16" fill="none" stroke="{_OUTLINE}" stroke-width="3" stroke-linecap="round"/>
        <path d="M63 21 C52 19 49 11 50 8 C59 8 65 12 65 20 Z" fill="{accent}" stroke="{_OUTLINE}" stroke-width="2.5"/>
        <path d="M65 18 C70 10 79 9 82 11 C80 19 72 23 65 22 Z" fill="{accent}" stroke="{_OUTLINE}" stroke-width="2.5"/>
        '''
    if accessory == "bow":
        return f'''
        <path d="M64 31 C55 20 43 21 42 30 C42 38 52 40 62 34 Z" fill="{accent}" stroke="{_OUTLINE}" stroke-width="3"/>
        <path d="M64 31 C73 20 85 21 86 30 C86 38 76 40 66 34 Z" fill="{accent}" stroke="{_OUTLINE}" stroke-width="3"/>
        <circle cx="64" cy="32" r="5" fill="{accent}" stroke="{_OUTLINE}" stroke-width="3"/>
        '''
    if accessory == "glasses":
        return f'''
        <circle cx="51" cy="63" r="10" fill="none" stroke="{accent}" stroke-width="3.5"/>
        <circle cx="77" cy="63" r="10" fill="none" stroke="{accent}" stroke-width="3.5"/>
        <path d="M61 63 H67" stroke="{accent}" stroke-width="3.5" stroke-linecap="round"/>
        '''
    if accessory == "crown":
        return f'''
        <path d="M47 33 L44 17 L56 24 L64 12 L72 24 L84 17 L81 34 Z"
              fill="{accent}" stroke="{_OUTLINE}" stroke-width="3" stroke-linejoin="round"/>
        <circle cx="64" cy="25" r="2.3" fill="{_WHITE}"/>
        '''
    return ""


def render_template_svg(options: TemplateOptions, *, pose: str = "idle") -> str:
    """Render one cute template frame as a self-contained transparent SVG."""
    _validate_options(options)
    if pose not in {"idle", "breathe", "blink", "squish", "hop"}:
        raise ValueError(f"Unknown template pose: {pose}")

    palette = PALETTES[options.palette]
    if pose == "breathe":
        transform = "translate(1 4) scale(0.985 0.965)"
    elif pose == "squish":
        transform = "translate(-2 9) scale(1.035 0.91)"
    elif pose == "hop":
        transform = "translate(1 -7) scale(0.985 1.02)"
    else:
        transform = ""

    blush = f'''
      <ellipse cx="39" cy="74" rx="6" ry="3.2" fill="{palette['blush']}" opacity="0.72"/>
      <ellipse cx="89" cy="74" rx="6" ry="3.2" fill="{palette['blush']}" opacity="0.72"/>
    '''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <g transform="{transform}">
    {_body_svg(options.body, palette['main'], palette['shadow'])}
    {blush}
    {_eyes_svg(options.eyes, closed=pose == 'blink')}
    {_mouth_svg(options.mouth)}
    {_accessory_svg(options.accessory, palette['accent'])}
  </g>
</svg>
'''


def write_template_preview(
    destination: str | Path,
    options: TemplateOptions,
) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_template_svg(options), encoding="utf-8")
    return path


def create_template_pet_manifest(
    workspace: str | Path,
    options: TemplateOptions,
    *,
    name: str = "My Deskling",
) -> PetManifest:
    """Create a lively starter pet entirely from mix-and-match template parts."""
    _validate_options(options)
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)

    frame_specs = {
        "idle": (
            ("frame_001.svg", "idle", 650),
            ("frame_002.svg", "breathe", 520),
        ),
        "blink": (
            ("frame_001.svg", "idle", 55),
            ("frame_002.svg", "blink", 100),
            ("frame_003.svg", "idle", 55),
        ),
        "bounce": (
            ("frame_001.svg", "idle", 70),
            ("frame_002.svg", "squish", 95),
            ("frame_003.svg", "hop", 110),
            ("frame_004.svg", "idle", 90),
        ),
    }

    animations: dict[str, AnimationConfig] = {}
    for animation_name, specs in frame_specs.items():
        frames: list[FrameConfig] = []
        for filename, pose, duration_ms in specs:
            relative = Path("sprites") / animation_name / filename
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_template_svg(options, pose=pose), encoding="utf-8")
            frames.append(FrameConfig(file=relative, duration_ms=duration_ms))
        animations[animation_name] = AnimationConfig(
            name=animation_name,
            frames=tuple(frames),
            mode="loop" if animation_name == "idle" else "once",
        )

    manifest = PetManifest(
        schema_version=1,
        root=root,
        pet=PetSettings(
            name=name.strip() or "My Deskling",
            width=128,
            height=128,
            scale=2.0,
            default_state="idle",
            default_animation="idle",
        ),
        animations=animations,
        transitions={
            "idle": {"reaction", "dragging"},
            "reaction": {"idle", "dragging"},
            "dragging": {"idle"},
        },
        idle_behavior=BehaviorConfig(
            min_delay_ms=4500,
            max_delay_ms=9000,
            actions=(BehaviorActionConfig(name="blink", weight=1.0),),
        ),
        interaction=InteractionConfig(click_animation="bounce"),
    )
    validate_manifest(manifest)
    return manifest
