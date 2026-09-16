import argparse
import logging
import os
import sys
from pathlib import Path

from desktoppet.config import ManifestError, load_manifest
from desktoppet.core import Pet
from desktoppet.platforms import NullBackend
from desktoppet.platforms.linux import configure_display_backend


def _validate(path: str) -> int:
    try:
        manifest = load_manifest(path)
    except ManifestError as exc:
        print(f"Invalid pet: {exc}")
        return 1
    print(f"Valid pet: {manifest.pet.name}")
    print(f"Animations: {', '.join(sorted(manifest.animations))}")
    return 0


def _inspect(path: str) -> int:
    try:
        manifest = load_manifest(path)
    except ManifestError as exc:
        print(f"Invalid pet: {exc}")
        return 1

    print(f"Name: {manifest.pet.name}")
    print(f"Canvas: {manifest.pet.width}x{manifest.pet.height} @ {manifest.pet.scale}x")
    print(f"Default: state={manifest.pet.default_state}, animation={manifest.pet.default_animation}")
    print("Animations:")
    for animation in manifest.animations.values():
        print(f"  - {animation.name}: {len(animation.frames)} frame(s), {animation.mode.value}")
    print("Transitions:")
    for state, targets in sorted(manifest.transitions.items()):
        print(f"  - {state} -> {', '.join(sorted(targets)) or '(none)'}")
    return 0


def _simulate(path: str, ticks: int, step_ms: int) -> int:
    try:
        manifest = load_manifest(path)
    except ManifestError as exc:
        print(f"Invalid pet: {exc}")
        return 1

    backend = NullBackend()
    pet = Pet(manifest, backend)
    print(f"Started {manifest.pet.name}: {backend.last_frame.name if backend.last_frame else '(none)'}")
    for index in range(ticks):
        pet.tick(step_ms)
        frame = backend.last_frame.name if backend.last_frame else "(none)"
        print(f"{index + 1:02d}: state={pet.state:<9} frame={frame}")
    return 0


def _run(path: str, debug: bool) -> int:
    try:
        load_manifest(path)
    except ManifestError as exc:
        print(f"Invalid pet: {exc}")
        return 1

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    forced_xwayland = configure_display_backend(os.environ)
    if forced_xwayland:
        logging.getLogger(__name__).info(
            "GNOME Wayland detected; using XWayland for movable pet windows"
        )

    try:
        from desktoppet.platforms.linux_gtk import GtkPetApplication
    except (ImportError, ValueError) as exc:
        logging.getLogger(__name__).error(
            "GTK4/PyGObject is required for 'deskling run': %s", exc
        )
        return 1

    application = GtkPetApplication(path)
    return application.run([sys.argv[0]])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deskling", description="Deskling SDK developer tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a pet.toml and its assets")
    validate.add_argument("path")

    inspect = subparsers.add_parser("inspect", help="Show a pet project's resolved configuration")
    inspect.add_argument("path")

    simulate = subparsers.add_parser("simulate", help="Run the pet engine against a headless backend")
    simulate.add_argument("path")
    simulate.add_argument("--ticks", type=int, default=10)
    simulate.add_argument("--step-ms", type=int, default=250)

    run = subparsers.add_parser("run", help="Launch a pet in a transparent GTK desktop window")
    run.add_argument("path")
    run.add_argument("--debug", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = str(Path(args.path))
    if args.command == "validate":
        return _validate(path)
    if args.command == "inspect":
        return _inspect(path)
    if args.command == "simulate":
        return _simulate(path, args.ticks, args.step_ms)
    if args.command == "run":
        return _run(path, args.debug)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
