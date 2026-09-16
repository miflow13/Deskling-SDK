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
    DOUBLE_CLICK_WINDOW_MS = 450.0
    DOUBLE_CLICK_DISTANCE_PX = 18.0
    DRAG_THRESHOLD_PX = 5.0

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

        # Learning note:
        # Click and drag are two possible outcomes of ONE pointer sequence.
        # We intentionally do not attach a separate Gtk.GestureDrag anymore.
        # Independent GTK gestures can claim the same sequence and cancel each
        # other's later events. One GestureClick owns press/release; Deskling
        # promotes the press into a drag only after the pointer moves far enough.
        self._pointer_down = False
        self._drag_active = False
        self._press_pointer_x = 0.0
        self._press_pointer_y = 0.0
        self._press_window_x = 0.0
        self._press_window_y = 0.0

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
        click.connect("pressed", self._on_pointer_pressed)
        click.connect("released", self._on_pointer_released)
        widget.add_controller(click)

        # EventControllerMotion observes movement but does not compete as a
        # second gesture. It is mainly a fallback for backends where a global
        # pointer position is unavailable; XWayland uses backend sampling.
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_pointer_motion)
        widget.add_controller(motion)

    def _tick(self) -> bool:
        pet = self._pet
        if pet is None:
            return True

        now = time.monotonic()
        delta_ms = max(0, round((now - self._last_tick) * 1000))
        self._last_tick = now

        if self._pointer_down:
            self._update_pointer_interaction()

        pet.tick(delta_ms)
        return True

    def _on_pointer_pressed(
        self, _gesture: Gtk.GestureClick, n_press: int, x: float, y: float
    ) -> None:
        pet = self._pet
        backend = self._backend
        if pet is None or backend is None:
            return

        self._pointer_down = True
        self._drag_active = False
        self._press_window_x = pet.position.x
        self._press_window_y = pet.position.y

        pointer = backend.pointer_position()
        if pointer is not None:
            self._press_pointer_x = pointer.x
            self._press_pointer_y = pointer.y
        else:
            self._press_pointer_x = self._press_window_x + x
            self._press_pointer_y = self._press_window_y + y

        self._logger.debug(
            "Pointer press: gtk_n_press=%s x=%.1f y=%.1f screen_x=%.1f screen_y=%.1f",
            n_press,
            x,
            y,
            self._press_pointer_x,
            self._press_pointer_y,
        )

    def _on_pointer_motion(
        self, _controller: Gtk.EventControllerMotion, x: float, y: float
    ) -> None:
        if self._pointer_down:
            self._update_pointer_interaction(local_x=x, local_y=y)

    def _on_pointer_released(
        self, _gesture: Gtk.GestureClick, n_press: int, x: float, y: float
    ) -> None:
        pet = self._pet
        if pet is None:
            return

        # Catch movement that happened between the most recent 16 ms tick and
        # the release event before deciding whether this was a click or drag.
        self._update_pointer_interaction(local_x=x, local_y=y)

        if self._drag_active:
            pet.drag_end()
            self._logger.debug("Pointer release completed drag")
            self._click_tracker.reset()
        else:
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

        self._pointer_down = False
        self._drag_active = False

    def _update_pointer_interaction(
        self,
        *,
        local_x: float | None = None,
        local_y: float | None = None,
    ) -> bool:
        """Promote a press to a drag after movement passes the threshold."""
        pet = self._pet
        backend = self._backend
        if pet is None or backend is None or not self._pointer_down:
            return False

        pointer = backend.pointer_position()
        if pointer is not None:
            current_x = pointer.x
            current_y = pointer.y
        elif local_x is not None and local_y is not None:
            # Fallback coordinate frame for native backends without a global
            # pointer query. XWayland normally takes the branch above.
            current_x = self._press_window_x + local_x
            current_y = self._press_window_y + local_y
        else:
            return False

        if not self._drag_active:
            dx = current_x - self._press_pointer_x
            dy = current_y - self._press_pointer_y
            distance_squared = (dx * dx) + (dy * dy)
            threshold_squared = self.DRAG_THRESHOLD_PX * self.DRAG_THRESHOLD_PX
            if distance_squared < threshold_squared:
                return False

            if pet.state != "dragging" and not pet.states.can_transition("dragging"):
                return False

            # Start from the original press coordinate so DragController keeps
            # the exact pointer-to-window grab offset, then move to the current
            # pointer position.
            self._click_tracker.reset()
            pet.drag_start(self._press_pointer_x, self._press_pointer_y)
            self._drag_active = True
            self._logger.debug(
                "Pointer promoted to drag: dx=%.1f dy=%.1f",
                dx,
                dy,
            )

        pet.drag_move(current_x, current_y)
        return True
