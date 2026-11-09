"""Reusable synthetic hosts, providers and voice for Meridio Quick tests and captures."""
import threading

from PySide6.QtCore import QObject, Signal
from _fixtures import capannone_rho
from meridiana.assistant import providers


class KeyStore:
    """In-memory keys for tests. Never touches the operating system keyring."""
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, provider):
        return self.values.get(provider, "")

    def put(self, provider, value):
        self.values[provider] = value


class Voice(QObject):
    availableChanged = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self.on = False
        self.spoken = []

    def available(self):
        return True, ""

    def set_on(self, on):
        self.on = on

    def feed(self, text):
        self.spoken.append(text)

    def flush(self):
        pass

    def stop(self):
        self.spoken.clear()

    close = stop



class Host:
    def __init__(self):
        self.project = capannone_rho()
        self.edits = []

    def selection(self):
        return ("site", "")

    def phase(self):
        return "model"

    def phase_title(self):
        return "Model"

    def path(self):
        return None

    def checks(self):
        return []

    def energy(self):
        return {}

    def set_status(self, value):
        self.status = value

    def edit(self, title, change):
        self.edits.append(title)
        change(self.project)

    def preferences(self):
        pass



class Provider(providers.Provider):
    def __init__(self, cloud=False, text="**Ready**", events=None):
        super().__init__(model="test-model", family="openai", cloud=cloud)
        self.text, self.events = text, events
        self.requests = []

    def stream(self, system, messages, tools):
        self.requests.append((system, messages, tools, threading.get_ident()))
        yield from self.events if self.events is not None else (
            providers.Text(self.text), providers.Usage(12, 3), providers.Done("end"))

