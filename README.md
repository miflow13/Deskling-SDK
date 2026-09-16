# Deskling SDK

> The engine provides capabilities. The pet provides personality.

Deskling SDK is a small, composition-first, event-driven Python framework for building interactive desktop companions. The `desktoppet` package contains the reusable engine; individual pets provide data-only assets, configuration, and personality.

## MVP status

The v0.1 core includes animation playback, events, guarded states, movement, dragging, idle scheduling, TOML manifests, portable `.deskling` packages, a platform adapter boundary, developer CLI tools, multiple declarative example pets, and an early browser-based visual builder.

The Linux runner includes a GTK4 adapter that creates a transparent pet window, displays animation frames, ticks the core runtime, emits click events, and connects pointer dragging to the SDK movement system. On GNOME Wayland it uses XWayland for freely movable pet windows; compositors with gtk4-layer-shell support can use native Wayland positioning.

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

## Try the examples

Headless developer tools:

```bash
deskling validate examples/slime
deskling inspect examples/boo
deskling simulate examples/boo --ticks 12 --step-ms 250
```

Launch a visible GTK pet:

```bash
deskling run examples/slime
deskling run examples/boo
```

## Portable pet packages

A `.deskling` file is Deskling's portable, data-only pet package. It contains a root `pet.toml` plus the assets referenced by that manifest. Arbitrary Python, shell scripts, and executable plugins are not part of the pet format.

Build Boo into a package:

```bash
deskling pack examples/boo
```

That creates:

```text
examples/boo.deskling
```

The same developer commands work directly with the package:

```bash
deskling validate examples/boo.deskling
deskling inspect examples/boo.deskling
deskling simulate examples/boo.deskling
deskling run examples/boo.deskling --debug
```

Package loading checks archive paths and entry types before extraction, rejects entries that escape the package root, and materializes valid packages into a content-addressed cache.

## Deskling Studio

`studio/` contains Deskling Studio v0.1, a static visual pet builder that runs entirely in the browser. Artwork stays local to the browser; Studio does not require accounts, uploads, a backend, npm, or external runtime dependencies.

Run it locally from the repository root:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080/studio/`.

The first Studio workflow supports pet identity/canvas settings, idle frames, click and double-click reactions, animation timing/playback controls, a fake-desktop preview with dragging, live `pet.toml` generation, and direct `.deskling` export.

This creates the same package shape consumed by the Python SDK:

```text
Deskling Studio
      |
      v
pet.toml + sprites
      |
      v
.deskling package
      |
      v
Deskling SDK runtime
```

## Architecture

```text
Pet folder / .deskling package
  pet.toml + sprites + sounds
              |
              v
Package + config layer
  safe materialization + validation
              |
              v
PetManifest (declarative data)
              |
              v
Runtime builder
  config -> engine objects
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
        +-----+------+
        |            |
   NullBackend   GtkBackend
   tests/tools  visible Linux pet
```

The core package never imports GTK and never imports Mochi. New pets such as Boo can be added without changing SDK source code.
