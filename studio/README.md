# Deskling Studio

Deskling Studio is the browser-based visual builder for Deskling Pet Format v0.1.

The v0.1 builder is intentionally static and client-only:

- no account
- no backend
- no server uploads
- no npm/runtime dependencies
- pet artwork stays in the browser
- export produces a data-only `.deskling` ZIP package

## Run locally

The app uses ES modules, so serve the repository over HTTP rather than opening `index.html` with a `file://` URL.

From the repository root:

```bash
python -m http.server 8080
```

Then open:

```text
http://localhost:8080/studio/
```

## v0.1 workflow

1. Name the pet and choose its canvas/desktop scale.
2. Upload one or more idle frames.
3. Optionally upload click and double-click reaction frames.
4. Set playback mode and per-frame timing for each animation.
5. Preview animation playback, clicks, double-clicks, and dragging in the fake desktop.
6. Inspect the generated `pet.toml`.
7. Export a portable `.deskling` package.

The exported archive contains only the root `pet.toml` plus referenced sprite files. Studio does not include scripts or executable pet code.

## Test the exported package

With the Deskling SDK installed:

```bash
deskling validate my-deskling.deskling
deskling inspect my-deskling.deskling
deskling run my-deskling.deskling --debug
```

## Current limits

Studio v0.1 intentionally exposes a small subset of the format: idle animation, click reaction, double-click reaction, canvas size, scale, animation timing, and playback mode. Roaming, sounds, random behaviors, custom state graphs, and richer events can be added after the visual builder/export loop is proven.
