"""Method-level drawing/source evidence for the common compatibility inventory.

The drawing comparison uses real Qt events and the complete save payload. The
new matrix remains in progress until its last frozen-API run is complete.
"""

BASE = "quick.pianta.test_tools_parity.DrawingParity."
SOURCES = "quick.pianta.test_sources.SourceTests."
PHOTOS = "build/quick-foto/pianta/tools/"


def evidence(tests, photo="", missing=""):
    return {"quick_replacement": tests, "status": "in corso" if missing else "fatto",
            "classification": "da portare" if missing else "sostituita",
            "evidence": [tests] + ([PHOTOS + photo] if photo else []),
            "notes": missing or "[V] Eventi Qt su Widgets e Quick, snapshot integrale salvo modified, nessuna differenza."}


TOOLS_MAPPING = {
    "widget.test_plan.Drawing.test_a_building_is_drawn_with_clicks_and_closed_with_enter": evidence(
        BASE + "test_building_vertices_numbers_and_rectangle",
        "test_building_vertices_numbers_and_rectangle-outline-quick.png"),
    "widget.test_plan.Drawing.test_a_typed_length_gives_the_side": evidence(
        BASE + "test_building_vertices_numbers_and_rectangle"),
    "widget.test_plan.Drawing.test_escape_cancels_the_outline": evidence(
        BASE + "test_measure_and_escape_three_levels", "test_measure_and_escape_three_levels-esc-draft-cleared-quick.png"),
    "widget.test_plan.Drawing.test_escape_with_nothing_in_hand_leaves_the_tool": evidence(
        BASE + "test_measure_and_escape_three_levels", "test_measure_and_escape_three_levels-esc-select-quick.png"),
    "widget.test_plan.Drawing.test_a_rectangle_by_three_clicks": evidence(
        BASE + "test_rectangle_three_clicks_and_small_depth_beside_edge"),
    "widget.test_plan.Drawing.test_a_small_rectangle_closes_beside_an_edge": evidence(
        BASE + "test_rectangle_three_clicks_and_small_depth_beside_edge"),
    "widget.test_plan.Drawing.test_a_typed_length_and_turn": evidence(
        BASE + "test_building_vertices_numbers_and_rectangle"),
    "widget.test_plan.Drawing.test_shift_keeps_the_direction": evidence(
        BASE + "test_shift_press_holds_direction_and_release_unlocks"),
    "widget.test_roof_tools.PitchCard.test_the_card_takes_a_slope_then_a_ridge_refuses_one_under_the_eave_and_tab_swaps": evidence(
        BASE + "test_pitch_refuses_low_ridge_then_accepts_height_and_tab",
        "test_pitch_refuses_low_ridge_then_accepts_height_and_tab-eave-swapped-quick.png",
        "[V] Giro offscreen del metodo verde. Ultimo giro D3D: snapshot uguali, ma warning da nuove property Plan.qml lette durante aggiornamento API; da ripetere a API ferme."),
    "widget.test_roof_tools.PitchCard.test_a_typed_depth_closes_and_percent_gives_the_slope": evidence(
        BASE + "test_pitch_typed_depth_closes_after_percent"),
    "widget.test_roof_tools.PitchCard.test_a_third_click_is_the_point_of_arrival_and_r_draws_corner_by_corner": evidence(
        BASE + "test_pitch_fields_swap_and_close; " + BASE + "test_pitch_polygon_and_backspace",
        missing="Terzo clic, poligono quattro vertici e Backspace provati; manca il caso esatto del triangolo tre vertici del metodo Widgets."),
    "widget.test_roof_tools.PitchCard.test_tab_without_a_pitch_drawn_is_not_taken": evidence(
        BASE + "test_pitch_refuses_low_ridge_then_accepts_height_and_tab"),
    "widget.test_roof_tools.RidgeTool.test_two_clicks_in_a_rectangle_give_the_ridge_and_a_typed_height_goes_with_it": evidence(
        BASE + "test_ridge_height_and_automatic_second_point", "test_ridge_height_and_automatic_second_point-height-quick.png"),
    "widget.test_roof_tools.RidgeTool.test_an_l_takes_a_bent_ridge_closed_with_enter_and_a_click_outside_is_said": evidence(
        BASE + "test_l_building_bent_ridge_and_outside_refusal",
        "test_l_building_bent_ridge_and_outside_refusal-bent-ridge-quick.png"),
    "widget.test_map_sources.MapsPage.test_the_background_to_start_from_is_one_of_the_site_and_the_sources_are_rows_with_their_licence": evidence(
        SOURCES + "test_background_site_sources_and_licences; " + SOURCES + "test_qml_component_loads_with_complete_editor_fields",
        missing="Backend e componente QML verificati; viaggio della pagina reale scritto, in attesa finestra GPU libera."),
    "widget.test_map_sources.MapsPage.test_an_xyz_source_is_not_used_until_it_has_its_attribution_and_its_key_goes_to_the_keyring": evidence(
        SOURCES + "test_xyz_waits_for_attribution_and_secret_never_enters_payload",
        missing="Backend verificato con portachiavi finto; digitazione e dialog chiave su finestra reale da eseguire."),
    "widget.test_map_sources.MapsPage.test_a_wms_and_a_wmts_from_their_capabilities_with_the_network_asked_only_when_allowed": evidence(
        SOURCES + "test_wms_wmts_recorded_capabilities_and_privacy; " +
        SOURCES + "test_capabilities_request_is_async_uses_user_agent_and_refuses_stale_source",
        missing="Fixture WMS/WMTS e HTTP locale asincrono verificati; interazione scelta layer sulla finestra reale da verificare."),
}

for _key, _row in TOOLS_MAPPING.items():
    if _key.startswith('widget.test_roof_tools.') and 'warning da nuove property' in _row['notes']:
        _row['status'] = 'fatto'
        _row['notes'] = '[V] Ripetuto sul renderer nativo a thread con API ferme; snapshot uguali e nessun warning.'

for _key, _row in TOOLS_MAPPING.items():
    if _key.startswith('widget.test_map_sources.') and ('xyz_source' in _key or 'background_to_start' in _key):
        _row['quick_replacement'] += '; quick.pianta.test_sources.SourceWindowTests.test_xyz_editor_real_keys_secret_dialog_and_theme_photos'
        _row['status'] = 'fatto'
        _row['classification'] = 'sostituita'
        _row['notes'] = '[V] Prova della finestra isolata verde, Basic come app: digitazione, attribuzione obbligatoria, chiave nel portachiavi e foto chiaro/scuro a 480 px.'
