"""Linux display selection helpers that do not import GTK."""

from collections.abc import MutableMapping


def configure_display_backend(environment: MutableMapping[str, str]) -> bool:
    """Prefer XWayland for freely movable pet windows on GNOME Wayland.

    Mutter does not expose the layer-shell positioning protocol used by many
    other Wayland compositors. When an X11 display is available, forcing only
    the pet process through XWayland gives Deskling a small transparent window
    that can be positioned and dragged without changing the rest of the session.

    Set ``DESKLING_NATIVE_WAYLAND=1`` to opt out.
    """
    desktop = environment.get("XDG_CURRENT_DESKTOP", "").casefold()
    is_gnome_wayland = (
        environment.get("XDG_SESSION_TYPE", "").casefold() == "wayland"
        and "gnome" in desktop
        and bool(environment.get("DISPLAY"))
    )
    if not is_gnome_wayland or environment.get("DESKLING_NATIVE_WAYLAND") == "1":
        return False

    environment["GDK_BACKEND"] = "x11"
    return True
