# Deskling SDK

> The engine provides capabilities. The pet provides personality.

Deskling SDK is a small, composition-first, event-driven Python framework for building interactive desktop companions. The `desktoppet` package contains the reusable engine; individual pets provide assets, configuration, and personality.

## MVP status

The v0.1 core includes:

- frame and animation models
- loop, one-shot, and ping-pong playback
- event bus
- guarded state machine
- movement and screen-bound clamping
- drag interaction logic
- weighted idle behavior scheduling
- TOML pet manifests
- platform adapter protocol
- headless/null backend for tests and tooling
- CLI validation and inspection
- a tiny Slime example pet

A native Linux/GTK backend is intentionally the next layer rather than being coupled to the core. This keeps GTK and Wayland/XWayland details out of the engine and lets Mochi's proven desktop-window behavior become an adapter instead of an SDK dependency.

## Install for development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Try the example

```bash
deskling validate examples/slime
deskling inspect examples/slime
deskling simulate examples/slime --ticks 12 --step-ms 250
```

## Architecture

```text
Pet project
  assets + pet.toml + optional behavior code
                 |
                 v
Core SDK
  Pet + EventBus + StateController
  AnimationPlayer + MovementController
  DragController + BehaviorScheduler
                 |
                 v
PlatformBackend protocol
                 |
        +--------+--------+
        |                 |
   NullBackend       Linux/GTK adapter
    (now)               (next)
```

The core package never imports GTK and never imports Mochi.
