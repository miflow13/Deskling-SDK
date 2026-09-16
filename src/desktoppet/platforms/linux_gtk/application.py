"""Visible GTK4 application that connects desktop input to the core pet engine."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from desktoppet.config import load_manifest
from desktoppet.core import Pet
from desktoppet.interaction import ClickTracker

from .backend import GtkBackend


class GtkPetApplication(Gtk.Application):
    TICK_MS = 16
    DRAG_CLICK_SUPPRESSION_S = 0.15
    DOUBLE_CLICK_WINDOW_MS = 450.0
    DOUBLE_CLICK_DISTANCE_PX = 18.0

    def __init__(self, project_path: str | Path) -> None:
        super().__init__(
            application_id="io.github.deskling.SDK.PetRunner",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.project_path = Path(project_path)
        self._pet: Pet | None = None
        self._backend: GtkBackend | None = None
        self._logger = logging.getLogger(__name__)
        self._last_tick = 0.0
        self._tick_source: int | None = None
        self._drag_active = False
        self._drag_origin_x = 0.0
        self._drag_origin_y = 0.0
        self._drag_start_x = 0.0
        self._drag_start_y = 0.0
        self._suppress_click_until = 0.0
        self._click_tracker = ClickTracker(
            double_click_ms=self.DOUBLE_CLICK_WINDOW_MS,
            max_distance_px=self.DOUBLE_CLICK_DISTANCE_PX,
        )

    def do_activate(self) -> None:
        existing = self.get_active_window()
        if existing is not None:
            existing.present()
            return

        manifest = load_manifest(self.project_path)
        width = manifest.pet.width * manifest.pet.scale
        height = manifest.pet.height * manifest.pet.scale

        window = Gtk.ApplicationWindow(application=self)
        window.set_title(manifest.pet.name)
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_focusable(False)
        window.set_default_size(width, height)
        window.add_css_class("deskling-pet-window")

        picture = Gtk.Picture()
        picture.set_can_shrink(False)
        picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        picture.set_size_request(width, height)
        window.set_child(picture)

        css = Gtk.CssProvider()
        css.load_from_string(
            "window.deskling-pet-window { background-color: transparent; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            window.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        backend = GtkBackend(window, picture)
        pet = Pet(manifest, backend)
        self._backend = backend
        self._pet = pet
        self._attach_input(picture)

        window.present()
        self._last_tick = time.monotonic()
        self._tick_source = GLib.timeout_add(self.TICK_MS, self._tick)

    def do_shutdown(self) -> None:
        if self._tick_source is not None:
            GLib.source_remove(self._tick_source)
            self._tick_source = None
        Gtk.Application.do_shutdown(self)

    def _attach_input(self, widget: Gtk.Widget) -> None:
        click = Gtk.GestureClick()
        click.set_button(1)
        # Learning note:
        # Do not trust GTK's n_press for double-click behavior. Some gesture
        # combinations reset or claim GTK's multi-click sequence. Deskling uses
        # completed click releases plus its own ClickTracker instead.
        click.connect("released", self._on_click_released)
        widget.add_controller(click)

        drag = Gtk.GestureDrag()
        drag.set_button(1)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        widget.add_controller(drag)

    def _tick(self) -> bool:
        pet = self._pet
        if pet is None:
            return True
        now = time.monotonic()
        delta_ms = max(0, round((now - self._last_tick) * 1000))
        self._last_tick = now
        if self._drag_active:
            self._sample_global_drag()
        pet.tick(delta_ms)
        return True

    def _on_click_released(
        self, _gesture: Gtk.GestureClick, n_press: int, x: float, y: float
    ) -> None:
        pet = self._pet
        if pet is None:
            return

        # GTK may report a release-click around the same pointer sequence used
        # for a drag. Do not let dropping the pet accidentally trigger a click
        # reaction. The short deadline also covers callback ordering after drag-end.
        if self._drag_active or time.monotonic() < self._suppress_click_until:
            self._click_tracker.reset()
            return

        # We intentionally ignore GTK's n_press here. Our own tracker makes
        # double-click recognition deterministic across GTK/XWayland setups.
        timestamp_ms = time.monotonic() * 1000.0
        clicks = self._click_tracker.register(timestamp_ms, x, y)
        self._logger.debug(
            "Pointer release: gtk_n_press=%s deskling_clicks=%s x=%.1f y=%.1f",
            n_press,
            clicks,
            x,
            y,
        )
        pet.handle_click(clicks, x=x, y=y)

    def _on_drag_begin(self, _gesture: Gtk.GestureDrag, x: float, y: float) -> None:
        pet = self._pet
        backend = self._backend
        if pet is None or backend is None:
            return
        if pet.state != "dragging" and not pet.states.can_transition("dragging"):
            return

        # Once pointer movement becomes a drag, it must not combine with a prior
        # click to form a false double-click later.
        self._click_tracker.reset()
        self._drag_active = True
        self._drag_origin_x = pet.position.x
        self._drag_origin_y = pet.position.y
        self._drag_start_x = x
        self._drag_start_y = y

        pointer = backend.pointer_position()
        if pointer is not None:
            pet.drag_start(pointer.x, pointer.y)
        else:
            pet.drag_start(self._drag_origin_x + x, self._drag_origin_y + y)

    def _on_drag_update(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        pet = self._pet
        if pet is None or not self._drag_active:
            return
        if self._sample_global_drag():
            return

        pet.drag_move(
            self._drag_origin_x + self._drag_start_x + offset_x,
            self._drag_origin_y + self._drag_start_y + offset_y,
        )

    def _on_drag_end(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        pet = self._pet
        if pet is None or not self._drag_active:
            return

        if not self._sample_global_drag():
            pet.drag_move(
                self._drag_origin_x + self._drag_start_x + offset_x,
                self._drag_origin_y + self._drag_start_y + offset_y,
            )
        pet.drag_end()
        self._drag_active = False
        self._click_tracker.reset()
        self._suppress_click_until = time.monotonic() + self.DRAG_CLICK_SUPPRESSION_S

    def _sample_global_drag(self) -> bool:
        pet = self._pet
        backend = self._backend
        if pet is None or backend is None or not self._drag_active:
            return False

        pointer = backend.pointer_position()
        if pointer is None:
            return False
        pet.drag_move(pointer.x, pointer.y)
        return True
