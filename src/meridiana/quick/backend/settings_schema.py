"""Translated presentation of the existing Config, without a second settings format."""
from meridiana import navigation, reports, tiles
from .settings_text import _
from meridiana.ui.appearance import font_names, place_names, text_size_names, toolbar_names
from meridiana.ui.preferences import orbit_names, pivot_names
from meridiana.ui.theme import background_names, colour_names, theme_names


SECTIONS = {
    'appearance': ('theme', 'accent', 'backgrounds', 'text_size', 'font', 'toolbar', 'toolbar_place',
                   'menu_bar', 'language', 'reduced_motion', 'strings_view', 'checks_view', 'help_open'),
    'navigation': ('navigation', 'orbit', 'pivot', 'pivot_hint'),
    'keyboard': ('shortcuts',),
    'assistant': ('assistant', 'assistant_docked', 'assistant_animated', 'assistant_style',
                  'assistant_width', 'assistant_height', 'assistant_provider', 'assistant_local_url',
                  'assistant_local_model', 'assistant_local_runtime', 'assistant_cloud_model',
                  'assistant_cloud_profiles', 'assistant_consent', 'assistant_voice', 'assistant_voice_engine',
                  'assistant_voice_name', 'assistant_voice_pitch', 'assistant_voice_speed', 'assistant_kokoro_dir',
                  'assistant_kokoro_python'),
    'report': ('report_profiles', 'report_profile'),
    'maps': ('background', 'map_sources', 'veil'),
    'privacy': ('network_geocoding', 'network_pvgis', 'network_tiles', 'check_updates', 'auto_install_updates'),
    # the 3D's edges (study 41, slice E, config v31), the memory (R548, config v32: in place of the share of R435,
    # config v27) and the year computed again in the background (R461, config v28)
    'performance': ('edges_3d', 'memory_mode', 'background_year', 'background_year_wait_s', 'background_year_workers',
                    'background_year_battery_factor'),
}
# Application bookkeeping is preserved, never presented as a user preference.
INTERNAL_FIELDS = ('extra', 'notices', 'pending_update', 'tour_status', 'tour_step', 'last_update_check',
                   'last_folder', 'last_project', 'recent', 'inverter_brand_favourites', 'assistant_introduced',
                   'layout_defaults',       # R523: kept from the Plant's Panels card («Keep in the profile»)
                   'memory_share')          # R548: the share of versions 27-31, kept for them (memory_mode now)
TABLE_FIELDS = {'shortcuts', 'report_profiles', 'map_sources', 'assistant_cloud_profiles', 'assistant_consent'}


def categories():
    return [{'key': key, 'label': label} for key, label in (
        ('appearance', _('Appearance')), ('navigation', _('Navigation')), ('keyboard', _('Keyboard')),
        ('assistant', _('Assistant')), ('report', _('Report')), ('maps', _('Maps')), ('privacy', _('Privacy')),
        ('performance', _('Performance')))]


def labels():
    return dict(theme=_('Theme'), accent=_('Colour'), backgrounds=_('Backgrounds'), text_size=_('Size of the text'),
                font=_('Font'), toolbar=_('Bar of the phase'), toolbar_place=_('Where'), menu_bar=_('&Menu bar').replace('&', ''),
                language=_('Language'), reduced_motion=_('Reduce motion'), strings_view=_('Strings'),
                checks_view=_('Checks'), help_open=_('Help'), navigation=_('Mouse style'), orbit=_('Orbit'),
                pivot=_('Centre of the orbit'), pivot_hint=_('Show the pivot on passing over'),
                assistant=_('Show {name}, the assistant, and its item in the status bar').format(name='Meridio'),
                assistant_docked=_('Dock the conversation in the panels, as Project and Properties'),
                assistant_animated=_('{name} animated: the rays turn, the eyes blink and glance, a face now and then').format(name='Meridio'), assistant_style=_('Drawing'),
                assistant_width=_('Width of the speech bubble'), assistant_height=_('Height of the speech bubble'),
                assistant_provider=_('Where {name} thinks').format(name='Meridio'), assistant_local_url=_('Local server'),
                assistant_local_model=_('Local model'), assistant_local_runtime=_('Kind of server'),
                assistant_cloud_model=_('Claude model'), assistant_voice=_('{name} reads his answers aloud, in the language of the program').format(name='Meridio'),
                assistant_voice_engine=_('Voice'), assistant_voice_name=_('Who speaks'),
                assistant_voice_pitch=_('Pitch, in semitones'), assistant_voice_speed=_('Speed'),
                assistant_kokoro_dir=_("Kokoro's model"), assistant_kokoro_python=_('Python for Kokoro'),
                report_profile=_('For the projects that choose none'), background=_('Start from'), veil=_('Veil over the map'),
                network_geocoding=_('Find the site'), network_pvgis=_('Weather and PVGIS'),
                network_tiles=_('Map tiles'), check_updates=_('Check for updates at start'),
                auto_install_updates=_('Install signed updates automatically'),
                edges_3d=_('Quality of the edges in the 3D'),
                memory_mode=_('Memory for what is kept and prepared ahead'),
                background_year=_('Compute the year again by itself when the changes stop'),
                background_year_wait_s=_('Seconds without changes before it starts'),
                background_year_workers=_('Processes for it'),
                background_year_battery_factor=_('On battery, the wait times'))


def choices(cfg):
    from meridiana.assistant.setup import CLOUD
    from meridiana.assistant.speech import voice_names
    return dict(theme=theme_names(), accent=colour_names(), backgrounds=background_names(),
                text_size=text_size_names(), font=font_names(), toolbar=toolbar_names(), toolbar_place=place_names(),
                language={'': _('Desktop language'), 'it': 'Italiano', 'en': 'English'},
                strings_view={'cards': _('Inputs as cards'), 'diagram': _('Single-line diagram in miniature')},
                checks_view={'level': _('By level'), 'object': _('By object'), 'area': _('By area'), 'delivery': _('Ready for delivery')},
                navigation=navigation.style_names(), orbit=orbit_names(), pivot=pivot_names(),
                edges_3d={'full': _('Highest'), 'moving': _('Reduced while the view moves'), 'low': _('Always reduced')},
                memory_mode={'save': _('Save memory'), 'auto': _('Automatic'), 'all': _('Use all of it')},
                assistant_style={'smooth': _('Smooth'), 'pixel': _('Pixel')},
                assistant_provider={'local': _('Local model, on this PC'), **{k: v.name for k, v in CLOUD.items()},
                                    'claude': 'Claude / Anthropic'},
                assistant_local_runtime={'': _('OpenAI-compatible (llama-server, LM Studio, Jan…)'), 'ollama': 'Ollama'},
                assistant_voice_engine={'auto': _('Automatic'), 'kokoro': 'Kokoro', 'system': _('System')},
                assistant_voice_name={'': _('Automatic: Sara in Italian, Michael in English'), **voice_names()},
                report_profile={reports.NOBODY: _('Nobody'),
                                **{p.get('name', ''): p.get('name', '') for p in cfg.report_profiles}},
                background={'auto': _('Automatic'), 'none': _('None'),
                            **{k: tiles.display_name(s) for k, s in tiles.catalogue(cfg.map_sources).items()}})


def descriptions():
    return {
        'assistant_voice_pitch': _('Higher is younger: the voice is resampled, so its pitch and its timbre rise together. Daniel chose +1 with Sara (R492).'),
        'assistant_voice_speed': _('1 is the speed of the model; Daniel chose 1.15. «Listen» reads a sentence with these settings.'),
        'assistant': _('Off, nothing of the assistant is left in the window: not the character, not the item in the status bar, not its key (Ctrl+L).'),
        'assistant_docked': _('Off, it floats over the views and the conversation opens as its speech bubble. The conversation is the same either way; the button at its head does the same.'),
        'assistant_animated': _('Off, or when the desktop asks for less motion, the character only changes expression with its state, and the speech bubble opens and closes at once.'),
        'network_geocoding': _("Find the site: the address typed goes to OpenStreetMap's Nominatim"),
        'network_pvgis': _("Weather and PVGIS estimate: the site's coordinates (five decimals) go to the European Commission's PVGIS"),
        'network_tiles': _('Map under the plan: the area in view goes to the server of the source in use.'),
        'check_updates': _('Updates: once a day at start, the Windows program asks GitHub whether a newer version is out; nothing about you or your projects is sent'),
        'auto_install_updates': _('Automatic installation waits until your project has no unsaved changes. You can cancel the download or turn this option off at any time.'),
        'font': _('The font of the whole window. The reports keep theirs'),
        'language': _('The language changes at the next start.'),
        'assistant_local_model': _('the one the server serves'),
        'background': _('Automatic takes the best source for the site of each project.'),
        'edges_3d': _('Smooth edges are the heaviest work of the graphics card on a 4K screen. Reduced while the view moves: while you turn, pan or zoom the 3D its edges are a little jagged and it runs smoother; they are smooth again as soon as you stop.'),
        'background_year': _('At low priority, with few processes: the numbers stay those of before until it ends.'),
        'background_year_workers': _('Processes of the electrical network, at low priority, from 1 to 8.'),
        'background_year_battery_factor': _('On battery it waits this many times longer, with one process; 0: never on battery.'),
    }


# the numbers' ranges in the Settings: the speech bubble's size (the default), the veil, the voice's pitch and
# speed (R492) and the background year (Performance, R435 R461); settings.py checks them
RANGES = {'size': dict(minimum=160, maximum=2400, decimals=0, step=10),
          'veil': dict(minimum=0, maximum=1, decimals=2, step=0.05),
          'assistant_voice_pitch': dict(minimum=-3, maximum=4, decimals=0, step=1),
          'assistant_voice_speed': dict(minimum=0.8, maximum=1.4, decimals=2, step=0.05),
          'background_year_wait_s': dict(minimum=1, maximum=120, decimals=0, step=1),
          'background_year_workers': dict(minimum=1, maximum=8, decimals=0, step=1),
          'background_year_battery_factor': dict(minimum=0, maximum=10, decimals=1, step=0.5)}


def fields_for(section, cfg):
    from meridiana import updates
    names, options, notes = labels(), choices(cfg), descriptions()
    result = []
    for key in SECTIONS[section]:
        if key in TABLE_FIELDS:
            continue
        value = cfg.extra.get(key, False) if key == 'reduced_motion' else getattr(cfg, key)
        kind = 'choice' if key in options else 'bool' if isinstance(value, bool) else 'number' if isinstance(value, (int, float)) else 'text'
        enabled = not (key == 'auto_install_updates' and (not cfg.check_updates or not updates.automatic_install_supported()))
        if key == 'pivot_hint':
            enabled = bool(navigation.orbit_key_text(cfg.navigation))
        note = memory_note() if key == 'memory_mode' else notes.get(key, '')
        result.append(dict(key=key, label=names[key], kind=kind, description=note, enabled=enabled,
                           options=[dict(value=k, label=v) for k, v in options.get(key, {}).items()],
                           **RANGES.get(key, RANGES['size']),
                           action='listen' if key == 'assistant_voice_speed' else '',
                           actionLabel=_('Listen') if key == 'assistant_voice_speed' else ''))
    return result


def memory_note() -> str:
    """What the three choices of the memory do, and what Meridiana holds now (R548): read when the section is shown."""
    from meridiana import resources
    from meridiana.i18n import number
    use = resources.in_use()
    gb = lambda b: number(b / resources.GIB, 1)
    head = _('Save memory: little is kept, nothing prepared ahead. Automatic: what the PC has free, less 2 GB for the rest, '
             'and the report and the IFC model prepared ahead when there is room. Use all of it: the same with 1 GB '
             'left, also on battery.')
    if not use['total']:
        return head
    now = _('Now: {window} GB the window, {helpers} GB the calculations; {free} GB free of {total}; '
            'what is kept may reach {budget} GB.').format(window=gb(use['window']), helpers=gb(use['helpers']),
                                                          free=gb(use['available']), total=gb(use['total']),
                                                          budget=gb(use['budget']))
    return head + ' ' + now
