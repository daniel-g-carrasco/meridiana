"""R649 (Daniel 15/11/2026: «usa il modello vocale inglese che legge di merda l'italiano»): the voice that reads an
answer is chosen by the language of the text it reads, not by the program's."""
import json
import unittest

from PySide6.QtCore import QCoreApplication

from meridiana.app.assistant import speech
from meridiana.gui.backend.voice import Kokoro, Voice


class Said:
    def __init__(self):
        self.said = []
        self.pitch = self.speed = 0

    def say(self, sentence, language=""):
        self.said.append((sentence, language))


class Pipe:
    def __init__(self):
        self.lines = []

    def write(self, data):
        self.lines.append(json.loads(data.decode('utf-8')))


class VoiceLanguageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(['r649'])

    def speaker(self, language):
        voice = Voice(language=language)
        voice.on, voice.ready, voice.kind = True, True, 'kokoro'
        voice.kokoro = Said()
        self.addCleanup(lambda: setattr(voice, 'kokoro', None))
        return voice

    def test_italian_text_with_the_program_in_english_is_read_in_italian(self):
        voice = self.speaker('en')
        voice.feed('Il rapporto di prestazione è basso perché le perdite per ombra sono alte. ')
        voice.feed('Sud. ')                       # says nothing by itself: the answer's language
        voice.flush()
        self.assertEqual([lang for _s, lang in voice.kokoro.said], ['it', 'it'])

    def test_english_text_with_the_program_in_italian_is_read_in_english(self):
        voice = self.speaker('it')
        voice.feed('The performance ratio is low because the shading losses are high.')
        voice.flush()
        self.assertEqual([lang for _s, lang in voice.kokoro.said], ['en'])

    def test_the_natural_voice_takes_the_voice_of_that_language(self):
        kokoro = Kokoro(folder=None, python='', voice=speech.default_voice('en'), language='en')
        kokoro.loaded, kokoro.process = True, Pipe()
        kokoro.say('Il rapporto è basso.', 'it')
        kokoro.say('The ratio is low.', 'en')
        kokoro.say('The ratio is low.')
        first, second, third = kokoro.process.lines
        self.assertEqual((first['lang'], first['voice']), ('it', speech.default_voice('it')))
        self.assertEqual((second['lang'], second['voice']), ('en', speech.default_voice('en')))
        self.assertEqual(third['lang'], 'en')


if __name__ == '__main__':
    unittest.main()
