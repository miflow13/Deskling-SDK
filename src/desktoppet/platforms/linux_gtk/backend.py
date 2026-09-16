"""GTK4 rendering and positioning adapter."""

from __future__ import annotations

import logging
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, Gtk  # noqa: E402

from desktoppet.movement import Bounds, Position

from .x11 import move_window, request_keep_above

try:
    gi.require_version("GdkWayland", "4.0")
    from gi.repository import GdkWayland  # type: ignore[attr-defined]  # noqa: E402
except (ImportError, ValueError):
    GdkWayland = None

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell  # type: ignore[attr-defined]  # noqa: E402
except (ImportError, ValueError):
    Gtk4LayerShell = None


class GtkBackend:
    """Render frames and position one transparent GTK pet window."""

    def __init__(self, window: Gtk.Window, picture: Gtk.Picture) -> None:
        self.window = window
        self.picture = picture
        self._logger = logging.getLogger(__name__)
        self._mapped = False
        self._pending_position = Position(0, 0)
        self._monitor = self._first_monitor()
        self.layer_shell_enabled = self._enable_layer_shell()
        self.window.connect("map", self._on_map)

    def get_bounds(self) -> Bounds:
        monitor = self._monitor
        if monitor is None:
            return Bounds(0, 0, 1920, 1080)

        geometry = monitor.get_geometry()
        if self.layer_shell_enabled:
            return Bounds(0, 0, geometry.width, geometry.height)
        return Bounds(
            geometry.x,
            geometry.y,
            geometry.x + geometry.width,
            geometry.y + geometry.height,
        )

    def show_frame(self, path: Path) -> None:
        self.picture.set_file(Gio.File.new_for_path(str(path)))

    def set_position(self, position: Position) -> None:
        self._pending_position = position
        x, y = round(position.x), round(position.y)

        if self.layer_shell_enabled and Gtk4LayerShell is not None:
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.LEFT, x)
            Gtk4LayerShell.set_margin(self.window, Gtk4LayerShell.Edge.TOP, y)
            return

        if self._mapped and not move_window(self.window, x, y):
            self._logger.debug("Window manager owns placement for this GTK surface")

    def _on_map(self, _window: Gtk.Window) -> None:
        self._mapped = True
        if not self.layer_shell_enabled:
            request_keep_above(self.window)
        self.set_position(self._pending_position)

    def _first_monitor(self) -> Gdk.Monitor | None:
        display = self.window.get_display()
        monitors = display.get_monitors()
        if monitors.get_n_items() == 0:
            return None
        return monitors.get_item(0)

    def _enable_layer_shell(self) -> bool:
        display = self.window.get_display()
        if GdkWayland is None or not isinstance(display, GdkWayland.WaylandDisplay):
            self._logger.info("Using GTK X11/XWayland window positioning")
            return False
        if Gtk4LayerShell is None or not Gtk4LayerShell.is_supported():
            self._logger.warning(
                "Native Wayland display has no layer-shell support; the pet will be visible "
                "but compositor-managed positioning may limit movement"
            )
            return False

        Gtk4LayerShell.init_for_window(self.window)
        Gtk4LayerShell.set_namespace(self.window, "deskling")
        Gtk4LayerShell.set_layer(self.window, Gtk4LayerShell.Layer.TOP)
        Gtk4LayerShell.set_keyboard_mode(self.window, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_exclusive_zone(self.window, -1)
        Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.TOP, True)
        if self._monitor is not None:
            Gtk4LayerShell.set_monitor(self.window, self._monitor)
        self._logger.info("Using native Wayland gtk4-layer-shell positioning")
        return True
