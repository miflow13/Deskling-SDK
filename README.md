# Deskling SDK

> The engine provides capabilities. The pet provides personality.

Deskling SDK is a small, composition-first, event-driven Python framework for building interactive desktop companions. The `desktoppet` package contains the reusable engine; individual pets provide data-only assets, configuration, and personality.

## MVP status

The v0.1 core includes animation playback, events, guarded states, movement, dragging, idle scheduling, TOML manifests, portable `.deskling` packages, a platform adapter boundary, developer CLI tools, multiple declarative example pets, and a native GTK4/Libadwaita Studio creator.

The Linux runner includes a GTK4 adapter that creates a transparent pet window, displays animation frames, ticks the core runtime, emits click events, and connects pointer dragging to the SDK movement system. On GNOME Wayland it uses XWayland for freely movable pet windows; compositors with gtk4-layer-shell support can use native Wayland positioning.

## Install for development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

GTK is a Linux system dependency rather than a normal Python package. On Fedora, install GTK/PyGObject and Libadwaita with your system package manager. If `import gi` works outside the venv but not inside it, recreate the environment with system packages visible:

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

Deskling Studio is a native GTK4/Libadwaita pet creator, so building and editing pets does not require hosting a website, running a browser builder, or hand-writing `pet.toml`.

Launch Studio:

```bash
deskling studio
```

Or open an existing pet immediately:

```bash
deskling studio examples/boo/pet.toml
deskling studio examples/boo.deskling
```

Native Studio can now:

- create a brand-new pet by choosing its first idle frame
- open `pet.toml` projects and `.deskling` packages
- edit pet name, canvas width/height, and desktop scale
- add new named animations
- import one or many image frames into an animation
- reorder and remove frames visually
- set each frame's duration in milliseconds
- switch playback between `once`, `loop`, and `pingpong`
- preview the selected animation using the edited timing
- export a validated `.deskling` package through the same SDK packer used by the CLI

Studio clones opened assets into an isolated temporary workspace before editing them. The source project or installed package cache is not rewritten when frames are rearranged or imported; changes become portable only when the user explicitly exports a new package.

The editor sits above the declarative config boundary rather than duplicating engine logic:

```text
Artwork / existing pet
        |
        v
Native Deskling Studio
  isolated workspace
        |
        v
PetManifest + assets
        |
        v
.deskling package
        |
        v
Deskling SDK runtime
```

The existing static browser prototype remains under `studio/` as a future hosted-web foundation, but the native application is the primary Studio experience for now.

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
