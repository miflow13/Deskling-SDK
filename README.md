# Deskling SDK

> The engine provides capabilities. The pet provides personality.

Deskling SDK is a small, composition-first, event-driven Python framework for building interactive desktop companions. The `desktoppet` package contains the reusable engine; individual pets provide assets, configuration, and personality.

## MVP status

The v0.1 core includes animation playback, events, guarded states, movement, dragging, idle scheduling, TOML manifests, a platform adapter boundary, developer CLI tools, and a Slime example.

The Linux runner now includes a GTK4 adapter that creates a transparent pet window, displays animation frames, ticks the core runtime, emits click events, and connects pointer dragging to the SDK movement system. On GNOME Wayland it uses XWayland for freely movable pet windows; compositors with gtk4-layer-shell support can use native Wayland positioning.

## Install for development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

GTK is a Linux system dependency rather than a normal Python package. On Fedora, install GTK/PyGObject with your system package manager. If `import gi` works outside the venv but not inside it, recreate the environment with system packages visible:

```bash
deactivate 2>/dev/null || true
rm -rf .venv
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Try the example

Headless developer tools:

```bash
deskling validate examples/slime
deskling inspect examples/slime
deskling simulate examples/slime --ticks 12 --step-ms 250
```

Launch the visible GTK pet:

```bash
deskling run examples/slime
```

Drag the Slime with the primary mouse button. Click and double-click events are emitted by the engine for pet-specific behavior code to subscribe to.

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
        +--------+---------+
        |                  |
   NullBackend         GtkBackend
   tests/tools        visible Linux pet
```

The core package never imports GTK and never imports Mochi.
