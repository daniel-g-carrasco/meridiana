"""Credential-free provider profiles exposed to QML. Saving never sends a request."""
from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from ...assistant import keys, setup
from ...i18n import _
from .assistant_local import LocalModels


class AssistantSetup(QObject):
    changed = Signal()
    configured = Signal(str)
    dismissed = Signal()

    def __init__(self, cfg, save_config=lambda: None, parent=None, *, key_store=None):
        super().__init__(parent)
        self.cfg, self.save_config = cfg, save_config
        self.keys = key_store if key_store is not None else keys
        provider = setup.canonical(cfg.assistant_provider)
        self._provider = provider if provider in setup.CLOUD else "openai"
        self._status = _("Saving makes no API request. Sending a question asks for consent first.")
        self._local = LocalModels(current=lambda: (cfg.assistant_local_url, cfg.assistant_local_model,
                                                   cfg.assistant_local_runtime), parent=self)
        self._local.chosen.connect(self.saveLocal)

    providers = Property("QVariantList", lambda self: [
        {"id": key, "text": spec.name, "docs": spec.docs} for key, spec in setup.CLOUD.items()], constant=True)
    provider = Property(str, lambda self: self._provider, notify=changed)
    model = Property(str, lambda self: setup.profile(self.cfg, self._provider)["model"], notify=changed)
    endpoint = Property(str, lambda self: setup.profile(self.cfg, self._provider)["endpoint"], notify=changed)
    accountUrl = Property(str, lambda self: setup.CLOUD[self._provider].docs, notify=changed)
    status = Property(str, lambda self: self._status, notify=changed)
    localModels = Property(QObject, lambda self: self._local, constant=True)

    @Slot(str)
    def chooseProvider(self, provider):
        provider = setup.canonical(provider)
        if provider in setup.CLOUD:
            self._provider = provider
            self.changed.emit()

    @Slot(str, str, str, str, result=bool)
    def saveCloud(self, provider, model, endpoint, key):
        provider = setup.canonical(provider)
        try:
            if provider not in setup.CLOUD:
                raise ValueError(_("Choose a provider."))
            model = model.strip()
            endpoint = setup.validate_endpoint(endpoint)
            if not model:
                raise ValueError(_("Enter the model ID from your provider account."))
            key = key.strip()
            if not key and not self.keys.get(provider):
                raise ValueError(_("Paste the API key from your provider account."))
            if key:
                self.keys.put(provider, key)
                setup.keys_changed()
            setup.remember(self.cfg, provider, model, endpoint)
            self.cfg.assistant_provider = provider
            self.save_config()
        except (ValueError, keys.KeyringMissing) as error:
            self._status = _("Configuration not saved: {why}").format(why=error)
            self.changed.emit()
            return False
        self._provider = provider
        self._status = _("Configured. Credentials and model access are checked only when you send a question.")
        self.changed.emit()
        self.configured.emit(provider)
        return True

    @Slot(str, str, str)
    def saveLocal(self, url, model, runtime):
        self.cfg.assistant_provider = "local"
        self.cfg.assistant_local_url = url
        self.cfg.assistant_local_model = model
        self.cfg.assistant_local_runtime = runtime
        self.save_config()
        self.changed.emit()
        self.configured.emit("local")

    @Slot()
    def openAccount(self):
        QDesktopServices.openUrl(QUrl(self.accountUrl))

    @Slot()
    def dismiss(self):
        self.dismissed.emit()

