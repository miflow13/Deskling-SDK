from __future__ import annotations

import re
from pathlib import Path

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from desktoppet.config import ManifestError, PetManifest, load_manifest
from desktoppet.package import PackageError

from .model import edit_pet_settings, export_manifest_package


APP_ID = "io.github.deskling.Studio"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "my-deskling"


class StudioWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        application: Adw.Application,
        initial_path: str | Path | None = None,
    ) -> None:
        super().__init__(application=application)
        self.set_title("Deskling Studio")
        self.set_default_size(1060, 720)

        self._manifest: PetManifest | None = None
        self._source_path: Path | None = None
        self._preview_source: int | None = None
        self._preview_animation: str | None = None
        self._preview_order: list[int] = []
        self._preview_cursor = 0

        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        toolbar = Adw.ToolbarView()
        self._toast_overlay.set_child(toolbar)

        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="Deskling Studio", subtitle="Native pet editor")
        header.set_title_widget(title)

        self._open_button = Gtk.Button(label="Open Pet…")
        self._open_button.connect("clicked", self._on_open_clicked)
        header.pack_start(self._open_button)

        self._export_button = Gtk.Button(label="Export .deskling")
        self._export_button.add_css_class("suggested-action")
        self._export_button.set_sensitive(False)
        self._export_button.connect("clicked", self._on_export_clicked)
        header.pack_end(self._export_button)
        toolbar.add_top_bar(header)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(390)
        paned.set_wide_handle(True)
        toolbar.set_content(paned)

        paned.set_start_child(self._build_editor())
        paned.set_end_child(self._build_preview())

        if initial_path is not None:
            GLib.idle_add(self._load_path, Path(initial_path))

    def _build_editor(self) -> Gtk.Widget:
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_width(330)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        scroller.set_child(box)

        intro = Gtk.Label(
            label=(
                "Open a pet.toml or .deskling package to inspect and edit it. "
                "Changes stay local until you export a new package."
            ),
            wrap=True,
            xalign=0,
        )
        intro.add_css_class("dim-label")
        box.append(intro)

        details_label = Gtk.Label(label="Pet details", xalign=0)
        details_label.add_css_class("title-3")
        box.append(details_label)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        box.append(grid)

        self._name_entry = Gtk.Entry()
        self._name_entry.set_sensitive(False)
        grid.attach(Gtk.Label(label="Name", xalign=0), 0, 0, 1, 1)
        grid.attach(self._name_entry, 1, 0, 1, 1)

        self._width_spin = Gtk.SpinButton.new_with_range(1, 4096, 1)
        self._width_spin.set_sensitive(False)
        grid.attach(Gtk.Label(label="Width", xalign=0), 0, 1, 1, 1)
        grid.attach(self._width_spin, 1, 1, 1, 1)

        self._height_spin = Gtk.SpinButton.new_with_range(1, 4096, 1)
        self._height_spin.set_sensitive(False)
        grid.attach(Gtk.Label(label="Height", xalign=0), 0, 2, 1, 1)
        grid.attach(self._height_spin, 1, 2, 1, 1)

        self._scale_spin = Gtk.SpinButton.new_with_range(0.25, 16.0, 0.25)
        self._scale_spin.set_digits(2)
        self._scale_spin.set_sensitive(False)
        grid.attach(Gtk.Label(label="Scale", xalign=0), 0, 3, 1, 1)
        grid.attach(self._scale_spin, 1, 3, 1, 1)

        source_label = Gtk.Label(label="Source", xalign=0)
        source_label.add_css_class("title-3")
        box.append(source_label)

        self._source_value = Gtk.Label(label="No pet open", xalign=0, wrap=True)
        self._source_value.set_selectable(True)
        self._source_value.add_css_class("dim-label")
        box.append(self._source_value)

        animations_label = Gtk.Label(label="Animations", xalign=0)
        animations_label.add_css_class("title-3")
        box.append(animations_label)

        self._animation_list = Gtk.ListBox()
        self._animation_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._animation_list.add_css_class("boxed-list")
        self._animation_list.connect("row-selected", self._on_animation_selected)
        box.append(self._animation_list)

        return scroller

    def _build_preview(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)

        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(heading)

        preview_label = Gtk.Label(label="Preview", xalign=0)
        preview_label.add_css_class("title-2")
        preview_label.set_hexpand(True)
        heading.append(preview_label)

        self._animation_name = Gtk.Label(label="No animation")
        self._animation_name.add_css_class("dim-label")
        heading.append(self._animation_name)

        frame = Gtk.Frame()
        frame.set_hexpand(True)
        frame.set_vexpand(True)
        box.append(frame)

        preview_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        preview_area.set_halign(Gtk.Align.FILL)
        preview_area.set_valign(Gtk.Align.FILL)
        preview_area.set_hexpand(True)
        preview_area.set_vexpand(True)
        preview_area.add_css_class("view")
        frame.set_child(preview_area)

        center = Gtk.CenterBox()
        center.set_hexpand(True)
        center.set_vexpand(True)
        preview_area.append(center)

        self._picture = Gtk.Picture()
        self._picture.set_can_shrink(True)
        self._picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self._picture.set_size_request(320, 320)
        center.set_center_widget(self._picture)

        self._preview_hint = Gtk.Label(
            label="Open a pet to preview its animation frames.",
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        self._preview_hint.add_css_class("dim-label")
        preview_area.append(self._preview_hint)

        self._manifest_summary = Gtk.Label(label="", xalign=0, wrap=True)
        self._manifest_summary.add_css_class("dim-label")
        box.append(self._manifest_summary)

        return box

    def _show_toast(self, message: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def _set_editor_sensitive(self, sensitive: bool) -> None:
        self._name_entry.set_sensitive(sensitive)
        self._width_spin.set_sensitive(sensitive)
        self._height_spin.set_sensitive(sensitive)
        self._scale_spin.set_sensitive(sensitive)
        self._export_button.set_sensitive(sensitive)

    def _clear_animation_rows(self) -> None:
        child = self._animation_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._animation_list.remove(child)
            child = next_child

    def _load_path(self, path: Path) -> bool:
        try:
            manifest = load_manifest(path)
        except (ManifestError, PackageError, OSError) as exc:
            self._show_toast(f"Could not open pet: {exc}")
            return False

        self._manifest = manifest
        self._source_path = path
        self._name_entry.set_text(manifest.pet.name)
        self._width_spin.set_value(manifest.pet.width)
        self._height_spin.set_value(manifest.pet.height)
        self._scale_spin.set_value(manifest.pet.scale)
        self._source_value.set_text(str(path))
        self._set_editor_sensitive(True)

        self._clear_animation_rows()
        first_row: Gtk.ListBoxRow | None = None
        for name, animation in manifest.animations.items():
            row = Gtk.ListBoxRow()
            row.animation_name = name  # type: ignore[attr-defined]

            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row_box.set_margin_top(9)
            row_box.set_margin_bottom(9)
            row_box.set_margin_start(12)
            row_box.set_margin_end(12)

            name_label = Gtk.Label(label=name, xalign=0)
            name_label.set_hexpand(True)
            row_box.append(name_label)

            meta = Gtk.Label(
                label=f"{len(animation.frames)} frame(s) · {animation.mode}",
                xalign=1,
            )
            meta.add_css_class("dim-label")
            row_box.append(meta)

            row.set_child(row_box)
            self._animation_list.append(row)
            if first_row is None:
                first_row = row

        self._manifest_summary.set_text(
            f"Pet Format v{manifest.schema_version} · "
            f"{len(manifest.animations)} animation(s) · "
            f"default: {manifest.pet.default_animation}"
        )
        self._preview_hint.set_text("Select an animation on the left to preview it.")

        if first_row is not None:
            self._animation_list.select_row(first_row)
        return False

    def _on_open_clicked(self, _button: Gtk.Button) -> None:
        chooser = Gtk.FileChooserNative.new(
            "Open Deskling Pet",
            self,
            Gtk.FileChooserAction.OPEN,
            "Open",
            "Cancel",
        )
        chooser.set_modal(True)

        package_filter = Gtk.FileFilter()
        package_filter.set_name("Deskling pets")
        package_filter.add_pattern("*.deskling")
        package_filter.add_pattern("pet.toml")
        chooser.add_filter(package_filter)

        chooser.connect("response", self._on_open_response)
        chooser.show()

    def _on_open_response(
        self, chooser: Gtk.FileChooserNative, response: int
    ) -> None:
        try:
            if response != Gtk.ResponseType.ACCEPT:
                return
            file = chooser.get_file()
            if file is None:
                return
            path = file.get_path()
            if path is None:
                self._show_toast("Deskling Studio can only open local files")
                return
            self._load_path(Path(path))
        finally:
            chooser.destroy()

    def _on_animation_selected(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if row is None:
            return
        name = getattr(row, "animation_name", None)
        if isinstance(name, str):
            self._start_preview(name)

    def _start_preview(self, animation_name: str) -> None:
        if self._preview_source is not None:
            GLib.source_remove(self._preview_source)
            self._preview_source = None

        manifest = self._manifest
        if manifest is None:
            return
        animation = manifest.animations.get(animation_name)
        if animation is None or not animation.frames:
            return

        count = len(animation.frames)
        order = list(range(count))
        if animation.mode == "pingpong" and count > 1:
            order.extend(range(count - 2, 0, -1))

        self._preview_animation = animation_name
        self._preview_order = order
        self._preview_cursor = 0
        self._animation_name.set_text(animation_name)
        self._advance_preview()

    def _advance_preview(self) -> bool:
        manifest = self._manifest
        animation_name = self._preview_animation
        if manifest is None or animation_name is None or not self._preview_order:
            return False

        animation = manifest.animations[animation_name]
        index = self._preview_order[self._preview_cursor]
        frame = animation.frames[index]
        self._picture.set_filename(str(manifest.root / frame.file))
        self._preview_hint.set_text(
            f"{frame.file.as_posix()} · {frame.duration_ms} ms"
        )

        self._preview_cursor += 1
        if self._preview_cursor >= len(self._preview_order):
            self._preview_cursor = 0

        self._preview_source = GLib.timeout_add(
            max(16, frame.duration_ms), self._advance_preview
        )
        return False

    def _edited_manifest(self) -> PetManifest:
        manifest = self._manifest
        if manifest is None:
            raise ManifestError("No pet is open")
        return edit_pet_settings(
            manifest,
            name=self._name_entry.get_text().strip(),
            width=self._width_spin.get_value_as_int(),
            height=self._height_spin.get_value_as_int(),
            scale=self._scale_spin.get_value(),
        )

    def _on_export_clicked(self, _button: Gtk.Button) -> None:
        if self._manifest is None:
            return
        try:
            manifest = self._edited_manifest()
        except ManifestError as exc:
            self._show_toast(f"Fix pet settings first: {exc}")
            return

        chooser = Gtk.FileChooserNative.new(
            "Export Deskling Pet",
            self,
            Gtk.FileChooserAction.SAVE,
            "Export",
            "Cancel",
        )
        chooser.set_modal(True)
        chooser.set_current_name(f"{_slugify(manifest.pet.name)}.deskling")

        package_filter = Gtk.FileFilter()
        package_filter.set_name("Deskling package (*.deskling)")
        package_filter.add_pattern("*.deskling")
        chooser.add_filter(package_filter)
        chooser.connect("response", self._on_export_response, manifest)
        chooser.show()

    def _on_export_response(
        self,
        chooser: Gtk.FileChooserNative,
        response: int,
        manifest: PetManifest,
    ) -> None:
        try:
            if response != Gtk.ResponseType.ACCEPT:
                return
            file = chooser.get_file()
            if file is None:
                return
            path_value = file.get_path()
            if path_value is None:
                self._show_toast("Deskling Studio can only export to local files")
                return
            path = Path(path_value)
            if path.suffix.lower() != ".deskling":
                path = path.with_suffix(".deskling")
            try:
                exported = export_manifest_package(manifest, path)
            except (ManifestError, PackageError, OSError) as exc:
                self._show_toast(f"Export failed: {exc}")
                return
            self._show_toast(f"Exported {exported.name}")
        finally:
            chooser.destroy()

    def do_close_request(self) -> bool:
        if self._preview_source is not None:
            GLib.source_remove(self._preview_source)
            self._preview_source = None
        return False


class StudioApplication(Adw.Application):
    def __init__(self, initial_path: str | Path | None = None) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.initial_path = initial_path

    def do_activate(self) -> None:
        window = self.get_active_window()
        if window is None:
            window = StudioWindow(self, self.initial_path)
        window.present()


def run_studio(path: str | Path | None = None) -> int:
    application = StudioApplication(path)
    return application.run([])
