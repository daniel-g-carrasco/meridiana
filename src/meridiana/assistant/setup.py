"""Provider choices and credential-free settings. No requests or downloads during setup.

Official protocol references checked 29 October 2026: the R07 provider report.
Model IDs are entered from the account's own catalogue: availability depends on account and region.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from ..i18n import _
from . import keys, providers


@dataclass(frozen=True)
class Cloud:
    name: str
    endpoint: str
    docs: str


CLOUD = {
    'openai': Cloud('GPT / OpenAI', 'https://api.openai.com/v1', 'https://platform.openai.com/api-keys'),
    'anthropic': Cloud('Claude / Anthropic', 'https://api.anthropic.com', 'https://platform.claude.com/'),
    'qwen': Cloud('Qwen / Alibaba Cloud', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
                  'https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope'),
    'gemini': Cloud('Gemini / Google', 'https://generativelanguage.googleapis.com/v1beta/openai',
                    'https://ai.google.dev/gemini-api/docs/openai'),
    'kimi': Cloud('Kimi / Moonshot', 'https://api.moonshot.ai/v1', 'https://platform.moonshot.ai/'),
    'mistral': Cloud('Mistral', 'https://api.mistral.ai/v1', 'https://console.mistral.ai/'),
    'deepseek': Cloud('DeepSeek', 'https://api.deepseek.com', 'https://api-docs.deepseek.com/'),
}


def canonical(provider: str) -> str:
    return 'anthropic' if provider == 'claude' else provider


def profile(cfg, provider: str) -> dict:
    """The provider's model and API address. The profile is the one source of truth; `assistant_cloud_model` is
    read only for an Anthropic profile without a model (settings written before format 23)."""
    provider = canonical(provider)
    saved = getattr(cfg, 'assistant_cloud_profiles', {}).get(provider, {})
    model = saved.get('model', '')
    if provider == 'anthropic' and not model:
        model = getattr(cfg, 'assistant_cloud_model', '')
    return {'model': model, 'endpoint': saved.get('endpoint') or CLOUD[provider].endpoint}


def remember(cfg, provider: str, model: str, endpoint: str = '') -> None:
    """The one place a cloud model is written, from the guided setup and from the chip's menu alike: the profile
    (a new table, so a copy of the settings never shares it). The legacy Anthropic field follows as a mirror."""
    provider = canonical(provider)
    profiles = {name: dict(values) for name, values in getattr(cfg, 'assistant_cloud_profiles', {}).items()}
    current = profile(cfg, provider)
    profiles[provider] = {'model': model, 'endpoint': endpoint or current['endpoint']}
    cfg.assistant_cloud_profiles = profiles
    if provider == 'anthropic':
        cfg.assistant_cloud_model = model


def validate_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip().rstrip('/')
    url = urlsplit(endpoint)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError(_('Use an HTTPS API address without a password, query or fragment.'))
    return endpoint


def available(cfg, get_key=keys.get) -> list[str]:
    """Configured, not a promise that billing or model access has been verified."""
    found = []
    for provider in CLOUD:
        try:
            settings = profile(cfg, provider)
            validate_endpoint(settings['endpoint'])
            if settings['model'].strip() and get_key(provider):
                found.append(provider)
        except (keys.KeyringMissing, ValueError):
            continue
    return found


_key_changes = 0                # how many times a key was stored or forgotten in this process


def keys_changed() -> None:
    """A key stored or forgotten (the guide, Settings): what every `Ready` remembers is read again."""
    global _key_changes
    _key_changes += 1


class Ready:
    """The providers configured (`available`), with the keyring asked once for each provider until a key may have
    changed (`keys_changed`, `forget`). The chat's chip is refreshed at every change of the project, and on Linux a
    locked keyring asks to be unlocked at each read: before R07 it was not read at all until a question went to the
    cloud. Only whether a key is there is kept, never the key."""

    def __init__(self, get_key):
        self.get_key = get_key
        self.known: dict[str, bool] = {}
        self.seen = _key_changes

    def forget(self) -> None:
        self.known.clear()

    def has_key(self, provider: str) -> bool:
        if self.seen != _key_changes:
            self.known.clear()
            self.seen = _key_changes
        if provider not in self.known:
            try:
                self.known[provider] = bool(self.get_key(provider))
            except keys.KeyringMissing:
                self.known[provider] = False        # no keyring here: said when a question needs the key
        return self.known[provider]

    def available(self, cfg) -> list[str]:
        return available(cfg, lambda provider: 'yes' if self.has_key(provider) else '')


def consent_id(cfg, provider: str) -> str:
    """Consent follows destination: changing the API address asks again."""
    provider = canonical(provider)
    endpoint = profile(cfg, provider)['endpoint'].rstrip('/')
    return provider if endpoint == CLOUD[provider].endpoint else provider + ':' + endpoint


def make(provider: str, settings: dict, key: str):
    provider = canonical(provider)
    if provider not in CLOUD:
        raise ValueError(_('Choose a provider.'))
    model = settings.get('model', '').strip()
    if not model or not key.strip():
        raise ValueError(_('Enter a model and an API key from your provider account.'))
    endpoint = validate_endpoint(settings.get('endpoint') or CLOUD[provider].endpoint)
    if provider == 'anthropic':
        # The menu's two models keep what task 14 chose for them (Haiku quick and cheap, Sonnet thinking more,
        # with the refusal fallback only at Anthropic's own address); a model typed by hand gets the API defaults.
        effort = {'claude-haiku-5-5': 'low', 'claude-sonnet-5-5': 'medium'}.get(model, '')
        fallbacks = model == 'claude-sonnet-5-5' and endpoint == CLOUD['anthropic'].endpoint
        return providers.Anthropic(model=model, key=key, base_url=endpoint, effort=effort, fallbacks=fallbacks)
    return providers.OpenAICompatible(model=model, key=key, base_url=endpoint, local=False, cloud=True,
                                      token_parameter='max_completion_tokens' if provider == 'openai' else 'max_tokens',
                                      include_usage=provider != 'mistral',
                                      extra_headers={'x-goog-api-client': 'meridiana'} if provider == 'gemini' else {})
