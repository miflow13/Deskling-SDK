from __future__ import annotations

from pathlib import Path
import tempfile

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .application import APP_ID, StudioApplication, StudioWindow
from .templates import (
    ACCESSORY_CHOICES,
    BODY_CHOICES,
    EYE_CHOICES,
    MOUTH_CHOICES,
    PALETTE_CHOICES,
    TemplateOptions,
    create_template_pet_manifest,
    write_template_preview,
)


class TemplateStudioWindow(StudioWindow):
    """Deskling Studio with a beginner-friendly mix-and-match pet builder."""

    def _build_editor(self) -> Gtk.Widget:
        editor = super()._build_editor()
        editor.set_vexpand(True)

        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        starter = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        starter.set_margin_top(16)
        starter.set_margin_bottom(12)
        starter.set_margin_start(18)
        starter.set_margin_end(18)
        starter.add_css_class("card")

        copy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        copy.set_hexpand(True)
        copy.set_margin_top(12)
        copy.set_margin_bottom(12)
        copy.set_margin_start(14)

        title = Gtk.Label(label="No artwork? Build a pet", xalign=0)
        title.add_css_class("heading")
        copy.append(title)

        subtitle = Gtk.Label(
            label="Mix cute bodies, faces, accessories, and colors — no drawing required.",
            xalign=0,
            wrap=True,
        )
        subtitle.add_css_class("dim-label")
        copy.append(subtitle)
        starter.append(copy)

        button = Gtk.Button(label="Pet Builder…")
        button.set_valign(Gtk.Align.CENTER)
        button.set_margin_end(14)
        button.add_css_class("suggested-action")
        button.connect("clicked", self._on_template_builder_clicked)
        starter.append(button)

        wrapper.append(starter)
        wrapper.append(editor)
        return wrapper

    @staticmethod
    def _choice_dropdown(values: tuple[str, ...]) -> Gtk.DropDown:
        return Gtk.DropDown.new_from_strings([value.replace("_", " ").title() for value in values])

    @staticmethod
    def _options_from_controls(
        body: Gtk.DropDown,
        eyes: Gtk.DropDown,
        mouth: Gtk.DropDown,
        accessory: Gtk.DropDown,
        palette: Gtk.DropDown,
    ) -> TemplateOptions:
        return TemplateOptions(
            body=BODY_CHOICES[body.get_selected()],
            eyes=EYE_CHOICES[eyes.get_selected()],
            mouth=MOUTH_CHOICES[mouth.get_selected()],
            accessory=ACCESSORY_CHOICES[accessory.get_selected()],
            palette=PALETTE_CHOICES[palette.get_selected()],
        )

    def _on_template_builder_clicked(self, _button: Gtk.Button) -> None:
        dialog = Gtk.Dialog(title="Build a Deskling", transient_for=self, modal=True)
        dialog.set_default_size(760, 540)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        create_button = dialog.add_button("Create Pet", Gtk.ResponseType.OK)
        create_button.add_css_class("suggested-action")
        dialog.set_default_response(Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)

        intro = Gtk.Label(
            label=(
                "Choose a few parts and Studio will build a ready-to-run pet with "
                "breathing, blinking, and a click bounce. You can edit every generated "
                "frame afterward."
            ),
            xalign=0,
            wrap=True,
        )
        intro.add_css_class("dim-label")
        content.append(intro)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        columns.set_vexpand(True)
        content.append(columns)

        form = Gtk.Grid(column_spacing=14, row_spacing=14)
        form.set_hexpand(True)
        form.set_valign(Gtk.Align.START)
        columns.append(form)

        name_entry = Gtk.Entry()
        name_entry.set_text("My Deskling")
        form.attach(Gtk.Label(label="Name", xalign=0), 0, 0, 1, 1)
        form.attach(name_entry, 1, 0, 1, 1)

        body = self._choice_dropdown(BODY_CHOICES)
        eyes = self._choice_dropdown(EYE_CHOICES)
        mouth = self._choice_dropdown(MOUTH_CHOICES)
        accessory = self._choice_dropdown(ACCESSORY_CHOICES)
        palette = self._choice_dropdown(PALETTE_CHOICES)

        controls = (
            ("Body", body),
            ("Eyes", eyes),
            ("Mouth", mouth),
            ("Accessory", accessory),
            ("Color", palette),
        )
        for row_index, (label, dropdown) in enumerate(controls, start=1):
            form.attach(Gtk.Label(label=label, xalign=0), 0, row_index, 1, 1)
            form.attach(dropdown, 1, row_index, 1, 1)

        preview_frame = Gtk.Frame()
        preview_frame.set_size_request(310, 310)
        preview_frame.set_hexpand(True)
        preview_frame.set_vexpand(True)
        columns.append(preview_frame)

        preview = Gtk.Picture()
        preview.set_can_shrink(True)
        preview.set_content_fit(Gtk.ContentFit.CONTAIN)
        preview.set_margin_top(20)
        preview.set_margin_bottom(20)
        preview.set_margin_start(20)
        preview.set_margin_end(20)
        preview_frame.set_child(preview)

        preview_temp = tempfile.TemporaryDirectory(prefix="deskling-builder-preview-")
        preview_root = Path(preview_temp.name)
        preview_counter = {"value": 0}

        def update_preview(*_args: object) -> None:
            options = self._options_from_controls(body, eyes, mouth, accessory, palette)
            preview_counter["value"] += 1
            path = write_template_preview(
                preview_root / f"preview-{preview_counter['value']:03d}.svg",
                options,
            )
            preview.set_filename(str(path))

        for _label, dropdown in controls:
            dropdown.connect("notify::selected", update_preview)
        update_preview()

        dialog.connect(
            "response",
            self._on_template_builder_response,
            name_entry,
            body,
            eyes,
            mouth,
            accessory,
            palette,
            preview_temp,
        )
        dialog.present()

    def _on_template_builder_response(
        self,
        dialog: Gtk.Dialog,
        response: int,
        name_entry: Gtk.Entry,
        body: Gtk.DropDown,
        eyes: Gtk.DropDown,
        mouth: Gtk.DropDown,
        accessory: Gtk.DropDown,
        palette: Gtk.DropDown,
        preview_temp: tempfile.TemporaryDirectory[str],
    ) -> None:
        try:
            if response != Gtk.ResponseType.OK:
                return

            options = self._options_from_controls(body, eyes, mouth, accessory, palette)
            workspace = self._new_workspace()
            manifest = create_template_pet_manifest(
                workspace,
                options,
                name=name_entry.get_text().strip(),
            )
            self._source_path = None
            self._set_manifest(
                manifest,
                source_label=(
                    "Template Builder · "
                    f"{options.body} + {options.eyes} + {options.mouth} + "
                    f"{options.accessory} · {options.palette}"
                ),
                select_animation="idle",
            )
            self._show_toast("Pet created — customize the generated animations or export it")
        except (OSError, ValueError) as exc:
            self._show_toast(f"Could not build pet: {exc}")
        finally:
            preview_temp.cleanup()
            dialog.destroy()


class TemplateStudioApplication(StudioApplication):
    def do_activate(self) -> None:
        window = self.get_active_window()
        if window is None:
            window = TemplateStudioWindow(self, self.initial_path)
        window.present()


def run_studio(path: str | Path | None = None) -> int:
    application = TemplateStudioApplication(path)
    return application.run([])
