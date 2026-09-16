from __future__ import annotations

import re
from pathlib import Path
import tempfile

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from desktoppet.config import ManifestError, PetManifest, load_manifest
from desktoppet.package import PackageError

from .model import (
    add_animation,
    add_frames,
    clone_manifest_to_workspace,
    create_new_pet_manifest,
    edit_pet_settings,
    export_manifest_package,
    move_frame,
    remove_frame,
    set_animation_mode,
    set_frame_duration,
)


APP_ID = "io.github.deskling.Studio"
PLAYBACK_MODES = ("once", "loop", "pingpong")
ANIMATION_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


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
        self.set_default_size(1180, 780)

        self._manifest: PetManifest | None = None
        self._source_path: Path | None = None
        self._workspace_temp: tempfile.TemporaryDirectory[str] | None = None
        self._preview_source: int | None = None
        self._preview_animation: str | None = None
        self._preview_order: list[int] = []
        self._preview_cursor = 0
        self._selected_animation: str | None = None
        self._updating_controls = False

        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        toolbar = Adw.ToolbarView()
        self._toast_overlay.set_child(toolbar)

        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="Deskling Studio", subtitle="Native pet creator")
        header.set_title_widget(title)

        self._new_button = Gtk.Button(label="New Pet…")
        self._new_button.connect("clicked", self._on_new_clicked)
        header.pack_start(self._new_button)

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
        paned.set_position(470)
        paned.set_wide_handle(True)
        toolbar.set_content(paned)

        paned.set_start_child(self._build_editor())
        paned.set_end_child(self._build_preview())

        if initial_path is not None:
            GLib.idle_add(self._load_path, Path(initial_path))

    def _build_editor(self) -> Gtk.Widget:
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_width(410)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        scroller.set_child(box)

        intro = Gtk.Label(
            label=(
                "Create a pet from artwork or open an existing pet.toml/.deskling. "
                "Studio works in an isolated local workspace until you export."
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

        animation_heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(animation_heading)

        animations_label = Gtk.Label(label="Animations", xalign=0)
        animations_label.add_css_class("title-3")
        animations_label.set_hexpand(True)
        animation_heading.append(animations_label)

        self._add_animation_button = Gtk.Button(label="Add Animation…")
        self._add_animation_button.set_sensitive(False)
        self._add_animation_button.connect("clicked", self._on_add_animation_clicked)
        animation_heading.append(self._add_animation_button)

        self._animation_list = Gtk.ListBox()
        self._animation_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._animation_list.add_css_class("boxed-list")
        self._animation_list.connect("row-selected", self._on_animation_selected)
        box.append(self._animation_list)

        edit_heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(edit_heading)

        self._selected_animation_label = Gtk.Label(label="Animation editor", xalign=0)
        self._selected_animation_label.add_css_class("title-3")
        self._selected_animation_label.set_hexpand(True)
        edit_heading.append(self._selected_animation_label)

        self._add_frames_button = Gtk.Button(label="Add Frames…")
        self._add_frames_button.set_sensitive(False)
        self._add_frames_button.connect("clicked", self._on_add_frames_clicked)
        edit_heading.append(self._add_frames_button)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.append(mode_row)
        mode_label = Gtk.Label(label="Playback", xalign=0)
        mode_label.set_hexpand(True)
        mode_row.append(mode_label)

        self._mode_dropdown = Gtk.DropDown.new_from_strings(list(PLAYBACK_MODES))
        self._mode_dropdown.set_sensitive(False)
        self._mode_dropdown.connect("notify::selected", self._on_mode_changed)
        mode_row.append(self._mode_dropdown)

        self._frame_list = Gtk.ListBox()
        self._frame_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._frame_list.add_css_class("boxed-list")
        box.append(self._frame_list)

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
        self._picture.set_size_request(360, 360)
        center.set_center_widget(self._picture)

        self._preview_hint = Gtk.Label(
            label="Create or open a pet to preview its animation frames.",
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

    def _new_workspace(self) -> Path:
        if self._workspace_temp is not None:
            self._workspace_temp.cleanup()
        self._workspace_temp = tempfile.TemporaryDirectory(prefix="deskling-studio-")
        return Path(self._workspace_temp.name)

    def _set_editor_sensitive(self, sensitive: bool) -> None:
        self._name_entry.set_sensitive(sensitive)
        self._width_spin.set_sensitive(sensitive)
        self._height_spin.set_sensitive(sensitive)
        self._scale_spin.set_sensitive(sensitive)
        self._export_button.set_sensitive(sensitive)
        self._add_animation_button.set_sensitive(sensitive)

    @staticmethod
    def _clear_listbox(listbox: Gtk.ListBox) -> None:
        child = listbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            listbox.remove(child)
            child = next_child

    def _stop_preview(self) -> None:
        if self._preview_source is not None:
            GLib.source_remove(self._preview_source)
            self._preview_source = None

    def _set_manifest(
        self,
        manifest: PetManifest,
        *,
        source_label: str,
        select_animation: str | None = None,
    ) -> None:
        self._manifest = manifest
        self._name_entry.set_text(manifest.pet.name)
        self._width_spin.set_value(manifest.pet.width)
        self._height_spin.set_value(manifest.pet.height)
        self._scale_spin.set_value(manifest.pet.scale)
        self._source_value.set_text(source_label)
        self._set_editor_sensitive(True)
        self._refresh_animation_rows(select_animation or manifest.pet.default_animation)
        self._update_summary()

    def _load_path(self, path: Path) -> bool:
        try:
            source_manifest = load_manifest(path)
            workspace = self._new_workspace()
            manifest = clone_manifest_to_workspace(source_manifest, workspace)
        except (ManifestError, PackageError, OSError, ValueError) as exc:
            self._show_toast(f"Could not open pet: {exc}")
            return False

        self._source_path = path
        self._set_manifest(manifest, source_label=str(path))
        return False

    def _update_summary(self) -> None:
        manifest = self._manifest
        if manifest is None:
            self._manifest_summary.set_text("")
            return
        total_frames = sum(len(animation.frames) for animation in manifest.animations.values())
        self._manifest_summary.set_text(
            f"Pet Format v{manifest.schema_version} · "
            f"{len(manifest.animations)} animation(s) · "
            f"{total_frames} frame(s) · "
            f"default: {manifest.pet.default_animation}"
        )

    def _refresh_animation_rows(self, select_name: str | None = None) -> None:
        manifest = self._manifest
        self._clear_listbox(self._animation_list)
        if manifest is None:
            return

        selected_row: Gtk.ListBoxRow | None = None
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
            if name == select_name:
                selected_row = row

        if selected_row is None:
            selected_row = first_row
        if selected_row is not None:
            self._animation_list.select_row(selected_row)

    def _refresh_frame_rows(self, animation_name: str) -> None:
        self._clear_listbox(self._frame_list)
        manifest = self._manifest
        if manifest is None:
            return
        animation = manifest.animations.get(animation_name)
        if animation is None:
            return

        self._selected_animation = animation_name
        self._selected_animation_label.set_text(f"Animation · {animation_name}")
        self._add_frames_button.set_sensitive(True)
        self._mode_dropdown.set_sensitive(True)

        self._updating_controls = True
        self._mode_dropdown.set_selected(PLAYBACK_MODES.index(animation.mode))
        self._updating_controls = False

        frame_count = len(animation.frames)
        for index, frame in enumerate(animation.frames):
            row = Gtk.ListBoxRow()
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_top(7)
            row_box.set_margin_bottom(7)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)

            thumbnail = Gtk.Picture.new_for_filename(str(manifest.root / frame.file))
            thumbnail.set_content_fit(Gtk.ContentFit.CONTAIN)
            thumbnail.set_size_request(42, 42)
            row_box.append(thumbnail)

            label = Gtk.Label(label=frame.file.name, xalign=0, ellipsize=3)
            label.set_hexpand(True)
            label.set_tooltip_text(frame.file.as_posix())
            row_box.append(label)

            duration = Gtk.SpinButton.new_with_range(16, 60000, 1)
            duration.set_value(frame.duration_ms)
            duration.set_tooltip_text("Frame duration in milliseconds")
            duration.connect(
                "value-changed",
                self._on_frame_duration_changed,
                animation_name,
                index,
            )
            row_box.append(duration)

            up = Gtk.Button(label="↑")
            up.set_sensitive(index > 0)
            up.set_tooltip_text("Move frame earlier")
            up.connect("clicked", self._on_move_frame, animation_name, index, -1)
            row_box.append(up)

            down = Gtk.Button(label="↓")
            down.set_sensitive(index < frame_count - 1)
            down.set_tooltip_text("Move frame later")
            down.connect("clicked", self._on_move_frame, animation_name, index, 1)
            row_box.append(down)

            remove = Gtk.Button(label="Remove")
            remove.set_sensitive(frame_count > 1)
            remove.add_css_class("destructive-action")
            remove.connect("clicked", self._on_remove_frame, animation_name, index)
            row_box.append(remove)

            row.set_child(row_box)
            self._frame_list.append(row)

    def _on_new_clicked(self, _button: Gtk.Button) -> None:
        chooser = Gtk.FileChooserNative.new(
            "Choose the first idle frame",
            self,
            Gtk.FileChooserAction.OPEN,
            "Create Pet",
            "Cancel",
        )
        chooser.set_modal(True)
        chooser.add_filter(self._image_filter())
        chooser.connect("response", self._on_new_response)
        chooser.show()

    def _on_new_response(
        self, chooser: Gtk.FileChooserNative, response: int
    ) -> None:
        try:
            if response != Gtk.ResponseType.ACCEPT:
                return
            file = chooser.get_file()
            if file is None:
                return
            path_value = file.get_path()
            if path_value is None:
                self._show_toast("Deskling Studio can only use local artwork")
                return
            try:
                workspace = self._new_workspace()
                manifest = create_new_pet_manifest(workspace, Path(path_value))
            except (OSError, ValueError, ManifestError) as exc:
                self._show_toast(f"Could not create pet: {exc}")
                return
            self._source_path = None
            self._set_manifest(
                manifest,
                source_label="New unsaved pet · local Studio workspace",
                select_animation="idle",
            )
            self._show_toast("New pet created — add frames or animations, then export")
        finally:
            chooser.destroy()

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

    @staticmethod
    def _image_filter() -> Gtk.FileFilter:
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image frames")
        image_filter.add_mime_type("image/*")
        image_filter.add_pattern("*.png")
        image_filter.add_pattern("*.svg")
        image_filter.add_pattern("*.webp")
        image_filter.add_pattern("*.gif")
        return image_filter

    @staticmethod
    def _chooser_paths(chooser: Gtk.FileChooserNative) -> list[Path]:
        files = chooser.get_files()
        paths: list[Path] = []
        for index in range(files.get_n_items()):
            file = files.get_item(index)
            if isinstance(file, Gio.File):
                path = file.get_path()
                if path is not None:
                    paths.append(Path(path))
        return paths

    def _on_add_animation_clicked(self, _button: Gtk.Button) -> None:
        if self._manifest is None:
            return

        dialog = Gtk.Dialog(title="Add Animation", transient_for=self, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Choose Frames…", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)

        name_entry = Gtk.Entry(placeholder_text="e.g. wave")
        content.append(Gtk.Label(label="Animation name", xalign=0))
        content.append(name_entry)

        mode_dropdown = Gtk.DropDown.new_from_strings(list(PLAYBACK_MODES))
        mode_dropdown.set_selected(0)
        content.append(Gtk.Label(label="Playback mode", xalign=0))
        content.append(mode_dropdown)

        dialog.connect(
            "response",
            self._on_add_animation_dialog_response,
            name_entry,
            mode_dropdown,
        )
        dialog.present()

    def _on_add_animation_dialog_response(
        self,
        dialog: Gtk.Dialog,
        response: int,
        name_entry: Gtk.Entry,
        mode_dropdown: Gtk.DropDown,
    ) -> None:
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        name = name_entry.get_text().strip()
        mode = PLAYBACK_MODES[mode_dropdown.get_selected()]
        if not ANIMATION_NAME_RE.fullmatch(name):
            self._show_toast(
                "Animation name may only use letters, numbers, '_' and '-'"
            )
            dialog.destroy()
            return
        if self._manifest is not None and name in self._manifest.animations:
            self._show_toast(f"Animation {name!r} already exists")
            dialog.destroy()
            return

        dialog.destroy()
        chooser = Gtk.FileChooserNative.new(
            f"Choose frames for {name}",
            self,
            Gtk.FileChooserAction.OPEN,
            "Add Animation",
            "Cancel",
        )
        chooser.set_modal(True)
        chooser.set_select_multiple(True)
        chooser.add_filter(self._image_filter())
        chooser.connect("response", self._on_add_animation_frames_response, name, mode)
        chooser.show()

    def _on_add_animation_frames_response(
        self,
        chooser: Gtk.FileChooserNative,
        response: int,
        animation_name: str,
        mode: str,
    ) -> None:
        try:
            if response != Gtk.ResponseType.ACCEPT or self._manifest is None:
                return
            paths = self._chooser_paths(chooser)
            try:
                self._manifest = add_animation(
                    self._manifest,
                    animation_name,
                    paths,
                    mode=mode,
                )
            except (ValueError, OSError, ManifestError) as exc:
                self._show_toast(f"Could not add animation: {exc}")
                return
            self._refresh_animation_rows(animation_name)
            self._update_summary()
            self._show_toast(f"Added animation {animation_name}")
        finally:
            chooser.destroy()

    def _on_add_frames_clicked(self, _button: Gtk.Button) -> None:
        animation_name = self._selected_animation
        if self._manifest is None or animation_name is None:
            return
        chooser = Gtk.FileChooserNative.new(
            f"Add frames to {animation_name}",
            self,
            Gtk.FileChooserAction.OPEN,
            "Add Frames",
            "Cancel",
        )
        chooser.set_modal(True)
        chooser.set_select_multiple(True)
        chooser.add_filter(self._image_filter())
        chooser.connect("response", self._on_add_frames_response, animation_name)
        chooser.show()

    def _on_add_frames_response(
        self,
        chooser: Gtk.FileChooserNative,
        response: int,
        animation_name: str,
    ) -> None:
        try:
            if response != Gtk.ResponseType.ACCEPT or self._manifest is None:
                return
            paths = self._chooser_paths(chooser)
            try:
                self._manifest = add_frames(self._manifest, animation_name, paths)
            except (ValueError, OSError, ManifestError) as exc:
                self._show_toast(f"Could not add frames: {exc}")
                return
            self._refresh_animation_rows(animation_name)
            self._update_summary()
            self._show_toast(f"Added {len(paths)} frame(s)")
        finally:
            chooser.destroy()

    def _on_animation_selected(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if row is None:
            self._selected_animation = None
            self._add_frames_button.set_sensitive(False)
            self._mode_dropdown.set_sensitive(False)
            self._clear_listbox(self._frame_list)
            return
        name = getattr(row, "animation_name", None)
        if isinstance(name, str):
            self._refresh_frame_rows(name)
            self._start_preview(name)

    def _on_mode_changed(self, dropdown: Gtk.DropDown, _param: object) -> None:
        if self._updating_controls or self._manifest is None:
            return
        animation_name = self._selected_animation
        if animation_name is None:
            return
        mode = PLAYBACK_MODES[dropdown.get_selected()]
        try:
            self._manifest = set_animation_mode(self._manifest, animation_name, mode)
        except (ValueError, ManifestError) as exc:
            self._show_toast(f"Could not change playback mode: {exc}")
            return
        self._refresh_animation_rows(animation_name)
        self._start_preview(animation_name)

    def _on_frame_duration_changed(
        self,
        spin: Gtk.SpinButton,
        animation_name: str,
        index: int,
    ) -> None:
        if self._manifest is None:
            return
        try:
            self._manifest = set_frame_duration(
                self._manifest,
                animation_name,
                index,
                spin.get_value_as_int(),
            )
        except (ValueError, IndexError, ManifestError) as exc:
            self._show_toast(f"Could not change frame timing: {exc}")
            return
        self._start_preview(animation_name)

    def _on_move_frame(
        self,
        _button: Gtk.Button,
        animation_name: str,
        index: int,
        direction: int,
    ) -> None:
        if self._manifest is None:
            return
        try:
            self._manifest = move_frame(
                self._manifest,
                animation_name,
                index,
                index + direction,
            )
        except (ValueError, IndexError, ManifestError) as exc:
            self._show_toast(f"Could not move frame: {exc}")
            return
        self._refresh_animation_rows(animation_name)
        self._update_summary()

    def _on_remove_frame(
        self,
        _button: Gtk.Button,
        animation_name: str,
        index: int,
    ) -> None:
        if self._manifest is None:
            return
        try:
            self._manifest = remove_frame(self._manifest, animation_name, index)
        except (ValueError, IndexError, ManifestError) as exc:
            self._show_toast(f"Could not remove frame: {exc}")
            return
        self._refresh_animation_rows(animation_name)
        self._update_summary()

    def _start_preview(self, animation_name: str) -> None:
        self._stop_preview()

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
            f"Frame {index + 1}/{len(animation.frames)} · "
            f"{frame.file.name} · {frame.duration_ms} ms"
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
        edited = edit_pet_settings(
            manifest,
            name=self._name_entry.get_text().strip(),
            width=self._width_spin.get_value_as_int(),
            height=self._height_spin.get_value_as_int(),
            scale=self._scale_spin.get_value(),
        )
        self._manifest = edited
        return edited

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
        self._stop_preview()
        if self._workspace_temp is not None:
            self._workspace_temp.cleanup()
            self._workspace_temp = None
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
