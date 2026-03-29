from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox,
    QGroupBox, QCheckBox, QPushButton, QLabel, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from pydantic_settings import BaseSettings
from pydantic import ValidationError
from pathlib import Path

from src.settings.settings import settings, reload, user_settings_file

import logging


_WINDOW_WIDTH = 800
_LABEL_WIDTH = 300


def _locate(schema: dict, path_: tuple[str, ...]):
    loc = schema
    for p in path_:
        loc = loc[p]

    return loc


def _field_from_schema(schema: dict, path_: tuple[str, ...]):
    field = _locate(schema, path_)
    type_ = field['type']
    format_ = field.get('format')

    if type_ == 'string' and format_ is None:
        return StringEdit(field)
    elif type_ == 'string' and format_ == 'path':
        return PathEdit(field)
    elif type_ == 'boolean':
        return BoolEdit(field)
    elif type_ == 'integer':
        return IntEdit(field)

    raise TypeError(f'Unknown type at {"/".join(path_)}: {type_}')


def _group_from_schema(schema: dict, path_: tuple[str, ...]):
    group = _locate(schema, path_)
    group_widget = SettingsBox(group['title'])

    for prop_name, prop_schema in group['properties'].items():

        if ref := prop_schema.get('$ref'):
            hash_, *ref = ref.split('/')
            assert hash_ == '#'

            subgroup = _group_from_schema(schema, tuple(ref))
            group_widget.add_group(prop_name, subgroup)

        else:
            field = _field_from_schema(schema, path_ + ('properties', prop_name))
            group_widget.add_property(prop_name, field)

    return group_widget


class PropertyEditMixin:
    def __init__(self, model: dict, parent=None):
        super().__init__(parent=parent)

        self._default = model['default']
        self.title = model['title']

    def set_value(self, value):
        raise NotImplementedError()

    def get_value(self) -> str:
        raise NotImplementedError()

    def restore_default(self):
        self.set_value(self._default)


class StringEdit(PropertyEditMixin, QLineEdit):
    def set_value(self, value: str):
        self.setText(str(value))

    def get_value(self) -> str:
        return self.text()


class PathEdit(PropertyEditMixin, QWidget):
    def __init__(self, model: dict, parent=None):
        super().__init__(model, parent)

        self._init_ui()

        self.browse_btn.clicked.connect(self.browse)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText('Enter or browse for path...')
        layout.addWidget(self.path_edit)

        self.browse_btn = QPushButton('Browse...')
        self.browse_btn.setFixedWidth(80)
        layout.addWidget(self.browse_btn)

    def browse(self):
        path_, _ = QFileDialog.getOpenFileName(
            self,
            'Select File',
            self.path_edit.text() or '',
            'JSON Files (*.json)'
        )

        if path_:
            self.path_edit.setText(path_)

    def set_value(self, path_: Path):
        self.path_edit.setText(str(path_))

    def get_value(self) -> Path:
        return Path(self.path_edit.text())


class IntEdit(PropertyEditMixin, QSpinBox):
    def __init__(self, model: dict, parent=None):
        super().__init__(model, parent)

        if (min_val := model.get('minimum')) is not None:
            self.setMinimum(min_val)
        elif (min_val := model.get('exclusiveMinimum')) is not None:
            self.setMinimum(min_val + 1)

        if (max_val := model.get('maximum')) is not None:
            self.setMaximum(max_val)
        elif (max_val := model.get('exclusiveMaximum')) is not None:
            self.setMaximum(max_val - 1)

        if model['maximum'] > 1000:
            self.setSingleStep(100)
        elif model['maximum'] > 100:
            self.setSingleStep(10)

    def set_value(self, value: int):
        self.setValue(value)

    def get_value(self) -> int:
        return self.value()


class BoolEdit(PropertyEditMixin, QCheckBox):
    def set_value(self, value: bool):
        self.setChecked(value)

    def get_value(self) -> bool:
        return self.isChecked()


PropertyEdit = StringEdit | IntEdit | BoolEdit | PathEdit


class SettingsBox(QGroupBox):
    def __init__(self, name: str, parent=None):
        super().__init__(name, parent=parent)

        self.properties: dict[str, PropertyEdit] = {}
        self.subgroups: dict[str, SettingsBox] = {}

        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)
        self.setLayout(self.main_layout)

        self.form_layout = QFormLayout()
        self.main_layout.addLayout(self.form_layout)

    def add_property(self, name: str, widget: PropertyEdit):
        self.properties[name] = widget
        label = QLabel(widget.title)
        label.setFixedWidth(_LABEL_WIDTH)
        self.form_layout.addRow(label, widget)

    def add_group(self, name: str, widget: SettingsBox):
        self.subgroups[name] = widget
        self.main_layout.addWidget(widget)

    def set_values(self, values: dict):
        for name, widget in self.properties.items():
            if value := values.get(name):
                widget.set_value(value)

        for name, widget in self.subgroups.items():
            if sub_values := values.get(name):
                widget.set_values(sub_values)

    def get_values(self):
        values = {name: widget.get_value() for name, widget in self.properties.items()}

        for name, widget in self.subgroups.items():
            values[name] = widget.get_values()

        return values

    def restore_defaults(self):
        for widget in self.properties.values():
            widget.restore_default()

        for widget in self.subgroups.values():
            widget.restore_defaults()


class SettingsForm(QWidget):
    quit_requested = Signal()

    def __init__(self, model: BaseSettings = settings, parent=None):
        super().__init__(parent=parent)

        self._model = model

        self._init_ui()

        self.settings_box.set_values(self._model.model_dump())

        self.save_and_quit_button.clicked.connect(self._save_and_quit)
        self.quit_no_save_button.clicked.connect(self.quit)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        self.settings_box = _group_from_schema(self._model.model_json_schema(), tuple())
        layout.addWidget(self.settings_box)

        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        self.save_and_quit_button = QPushButton('Save and quit')
        button_layout.addWidget(self.save_and_quit_button)

        self.quit_no_save_button = QPushButton('Quit without saving')
        button_layout.addWidget(self.quit_no_save_button)

        self.restore_defaults_button = QPushButton('Restore defaults')
        button_layout.addWidget(self.restore_defaults_button)

    def _save_and_quit(self):
        self.save()
        self.quit()

    def save(self):
        values = self.settings_box.get_values()
        try:
            self._model.model_validate(values)
        except ValidationError:
            logging.log(logging.WARNING, 'Could not save settings configuration: one or more values are invalid')
            return

        model = self._model.model_construct(**values)
        with open(user_settings_file, 'w') as f:
            f.write(model.model_dump_json(indent=2))

        reload()

    def quit(self):
        self.quit_requested.emit()

    def restore_defaults(self):
        self.settings_box.restore_defaults()


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setFixedWidth(_WINDOW_WIDTH)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window | Qt.WindowStaysOnTopHint)
        self.setObjectName('settings')

        self._init_ui()

        self.form.quit_requested.connect(self.close)

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.form = SettingsForm()
        layout.addWidget(self.form)
