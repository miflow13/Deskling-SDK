import argparse
from pathlib import Path

from desktoppet.config import ManifestError, load_manifest
from desktoppet.core import Pet
from desktoppet.platforms import NullBackend


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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
