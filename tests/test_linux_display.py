from desktoppet.platforms.linux import configure_display_backend


def test_gnome_wayland_prefers_xwayland() -> None:
    environment = {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "GNOME",
        "DISPLAY": ":0",
    }
    assert configure_display_backend(environment)
    assert environment["GDK_BACKEND"] == "x11"


def test_native_wayland_opt_out_is_respected() -> None:
    environment = {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "GNOME",
        "DISPLAY": ":0",
        "DESKLING_NATIVE_WAYLAND": "1",
    }
    assert not configure_display_backend(environment)
    assert "GDK_BACKEND" not in environment


def test_non_gnome_session_is_left_alone() -> None:
    environment = {
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "KDE",
        "DISPLAY": ":0",
    }
    assert not configure_display_backend(environment)
    assert "GDK_BACKEND" not in environment
