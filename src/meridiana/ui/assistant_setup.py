"""Guided local/cloud setup embedded in the conversation or Preferences. No LLM required."""
from __future__ import annotations

from PySide6.QtCore import Signal, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QFormLayout, QLabel, QLineEdit, QPushButton, QSizePolicy,
                               QStackedWidget, QVBoxLayout, QWidget)

from ..assistant import keys, setup
from ..i18n import _
from .style import Group


class SetupPages(QStackedWidget):
    """Only the current step contributes to the card's height."""
    def sizeHint(self):
        return self.currentWidget().sizeHint() if self.currentWidget() else super().sizeHint()

    def minimumSizeHint(self):
        return self.currentWidget().minimumSizeHint() if self.currentWidget() else super().minimumSizeHint()


class AssistantSetup(Group):
    configured = Signal(str)
    dismissed = Signal()
    layoutChanged = Signal()

    def __init__(self, cfg, save_config=lambda: None, parent=None):
        super().__init__(_('Give Meridio a model'), parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.cfg, self.save_config = cfg, save_config
        box = QVBoxLayout(self)
        intro = QLabel(_('I need a language model to answer you. Choose local or cloud and I will guide you. '
                         'The spoken voice is a separate setting.'))
        intro.setWordWrap(True)
        box.addWidget(intro)
        self.mode = QComboBox()
        self.mode.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.mode.setMinimumContentsLength(12)
        self.mode.addItem(_('Choose local or cloud'), 'choose')
        self.mode.addItem(_('On this PC: private, uses RAM and disk'), 'local')
        self.mode.addItem(_('Cloud: API account and usage charges'), 'cloud')
        box.addWidget(self.mode)
        self.pages = SetupPages()
        self.pages.addWidget(QWidget())
        self.local_page = QWidget()
        self.local_box = QVBoxLayout(self.local_page)
        self.pages.addWidget(self.local_page)
        cloud = QWidget()
        form = QFormLayout(cloud)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.provider = QComboBox()
        for key, provider in setup.CLOUD.items():
            self.provider.addItem(provider.name, key)
        form.addRow(_('Provider'), self.provider)
        self.account = QPushButton(_('API account and instructions'))
        self.account.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(setup.CLOUD[self.provider.currentData()].docs)))
        form.addRow(self.account)
        note = QLabel(_('Create an API key in your provider account, then paste it here. A chat subscription '
                        'does not necessarily include API credit. Choose a model enabled for your account. '
                        'Qwen endpoints depend on region and workspace: copy the address from its console.'))
        note.setWordWrap(True)
        form.addRow(note)
        self.model = QLineEdit()
        self.model.setPlaceholderText(_('Model ID from your account'))
        form.addRow(_('Model'), self.model)
        self.endpoint = QLineEdit()
        form.addRow(_('API address'), self.endpoint)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText(_('Stored only in the system keyring'))
        form.addRow(_('API key'), self.key)
        self.save = QPushButton(_('Save configuration'))
        self.save.clicked.connect(self.save_cloud)
        form.addRow(self.save)
        self.status = QLabel(_('Saving makes no API request. Sending a question asks for consent first.'))
        self.status.setWordWrap(True)
        form.addRow(self.status)
        self.pages.addWidget(cloud)
        box.addWidget(self.pages)
        self.cancel = QPushButton(_('Not now'))
        self.cancel.clicked.connect(self._dismiss)
        box.addWidget(self.cancel)
        self.mode.currentIndexChanged.connect(self._mode)
        self.provider.currentIndexChanged.connect(self._provider)
        chosen = self.provider.findData(setup.canonical(getattr(cfg, 'assistant_provider', 'local')))
        if chosen >= 0:
            self.provider.setCurrentIndex(chosen)
        self._provider()
        self._mode(self.mode.currentIndex())

    def _dismiss(self):
        self.key.clear()
        self.dismissed.emit()

    def _mode(self, index):
        if index == 1 and not hasattr(self, 'local_models'):
            from .assistant_local import LocalModels
            self.local_models = LocalModels(current=lambda: (
                getattr(self.cfg, 'assistant_local_url', ''), getattr(self.cfg, 'assistant_local_model', ''),
                getattr(self.cfg, 'assistant_local_runtime', '')))
            self.local_models.chosen.connect(self.save_local)
            self.local_box.addWidget(self.local_models)
        self.pages.setCurrentIndex(index)
        self.pages.setVisible(index != 0)
        self.pages.updateGeometry()
        self.updateGeometry()
        QTimer.singleShot(0, self, self.layoutChanged.emit)

    def _provider(self, _index=-1):
        settings = setup.profile(self.cfg, self.provider.currentData())
        self.model.setText(settings['model'])
        self.endpoint.setText(settings['endpoint'])
        self.key.clear()

    def save_cloud(self):
        provider = self.provider.currentData()
        try:
            model = self.model.text().strip()
            endpoint = setup.validate_endpoint(self.endpoint.text())
            if not model:
                raise ValueError(_('Enter the model ID from your provider account.'))
            key = self.key.text().strip()
            if not key and not keys.get(provider):
                raise ValueError(_('Paste the API key from your provider account.'))
            if key:
                keys.put(provider, key)
                setup.keys_changed()
            setup.remember(self.cfg, provider, model, endpoint)
            self.cfg.assistant_provider = provider
            self.save_config()
        except (ValueError, keys.KeyringMissing) as error:
            self.status.setText(_('Configuration not saved: {why}').format(why=error))
            return
        self.key.clear()
        self.status.setText(_('Configured. Credentials and model access are checked only when you send a question.'))
        self.configured.emit(provider)

    def save_local(self, url, model, runtime):
        self.cfg.assistant_provider = 'local'
        self.cfg.assistant_local_url = url
        self.cfg.assistant_local_model = model
        self.cfg.assistant_local_runtime = runtime
        self.save_config()
        self.configured.emit('local')
