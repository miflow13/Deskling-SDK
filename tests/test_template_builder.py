from ast import parse
from itertools import product
from pathlib import Path

from desktoppet.config import load_manifest
from desktoppet.studio import (
    ACCESSORY_CHOICES,
    BODY_CHOICES,
    EYE_CHOICES,
    MOUTH_CHOICES,
    PALETTE_CHOICES,
    TemplateOptions,
    create_template_pet_manifest,
    export_manifest_package,
    render_template_svg,
)


ROOT = Path(__file__).resolve().parents[1]


def test_every_starter_combination_renders_svg() -> None:
    combinations = product(
        BODY_CHOICES,
        EYE_CHOICES,
        MOUTH_CHOICES,
        ACCESSORY_CHOICES,
        PALETTE_CHOICES,
    )
    count = 0
    for body, eyes, mouth, accessory, palette in combinations:
        svg = render_template_svg(
            TemplateOptions(
                body=body,
                eyes=eyes,
                mouth=mouth,
                accessory=accessory,
                palette=palette,
            )
        )
        assert svg.startswith("<svg")
        assert 'viewBox="0 0 128 128"' in svg
        count += 1

    assert count == 675


def test_template_parts_actually_change_rendered_pet() -> None:
    base = render_template_svg(TemplateOptions())
    assert render_template_svg(TemplateOptions(body="ghost")) != base
    assert render_template_svg(TemplateOptions(eyes="sparkle")) != base
    assert render_template_svg(TemplateOptions(mouth="cat")) != base
    assert render_template_svg(TemplateOptions(accessory="bow")) != base
    assert render_template_svg(TemplateOptions(palette="lavender")) != base


def test_template_builder_creates_lively_valid_pet(tmp_path: Path) -> None:
    manifest = create_template_pet_manifest(
        tmp_path / "workspace",
        TemplateOptions(
            body="ghost",
            eyes="sparkle",
            mouth="cat",
            accessory="crown",
            palette="lavender",
        ),
        name="Twinkle",
    )

    assert manifest.pet.name == "Twinkle"
    assert manifest.pet.width == 128
    assert manifest.pet.height == 128
    assert list(manifest.animations) == ["idle", "blink", "bounce"]
    assert manifest.animations["idle"].mode == "loop"
    assert len(manifest.animations["idle"].frames) == 2
    assert len(manifest.animations["blink"].frames) == 3
    assert len(manifest.animations["bounce"].frames) == 4
    assert manifest.idle_behavior is not None
    assert manifest.idle_behavior.actions[0].name == "blink"
    assert manifest.interaction is not None
    assert manifest.interaction.click_animation == "bounce"

    for animation in manifest.animations.values():
        for frame in animation.frames:
            path = manifest.root / frame.file
            assert path.is_file()
            assert path.read_text(encoding="utf-8").startswith("<svg")


def test_template_pet_exports_and_reloads(tmp_path: Path) -> None:
    manifest = create_template_pet_manifest(
        tmp_path / "workspace",
        TemplateOptions(body="round", accessory="glasses", palette="sky"),
        name="Bubbles",
    )
    package = export_manifest_package(manifest, tmp_path / "bubbles.deskling")
    loaded = load_manifest(package)

    assert loaded.pet.name == "Bubbles"
    assert set(loaded.animations) == {"idle", "blink", "bounce"}
    assert loaded.idle_behavior is not None
    assert loaded.interaction is not None
    assert loaded.interaction.click_animation == "bounce"


def test_template_builder_ui_source_parses_without_importing_gtk() -> None:
    source = (
        ROOT / "src" / "desktoppet" / "studio" / "application_with_builder.py"
    ).read_text(encoding="utf-8")
    parse(source)
    assert "No artwork? Build a pet" in source
    assert "Pet Builder…" in source
