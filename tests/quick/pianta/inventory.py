"""Rebuild the method-by-method plan backlog without importing any Widgets module.

Run with PYTHONPATH=src;tests: python tests/quick/pianta/inventory.py.
The shared parity registry supplies stable test IDs. This narrower report never changes it.
"""

from __future__ import annotations

import ast
import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MATCH = re.compile(
    r'\b(?:plan_overlays|lit_modules|PlanView|plan_view)\b|'
    r'meridiana\.ui\.(?:plan|marks|symbols|tileloader|world_map|map_sources)\b|'
    r'from meridiana\.ui import[^\n]*(?:plan|marks|symbols|tileloader|world_map|map_sources)')

# A replacement means the same observable contract is asserted by the named Quick tests.
# Partial backend coverage is deliberately left in the backlog, with its narrower evidence.
REPLACEMENTS = {
    'widget.test_plan.Drawing.test_a_building_is_drawn_with_clicks_and_closed_with_enter':
        ('test_tools_parity.DrawingParity.test_building_vertices_numbers_and_rectangle',
         'Eventi Qt in entrambe le finestre e confronto del progetto completo dopo chiusura.'),
    'widget.test_plan.Drawing.test_a_typed_length_gives_the_side':
        ('test_tools_parity.DrawingParity.test_building_vertices_numbers_and_rectangle',
         'Lato numerico da eventi Qt e progetto completo confrontato.'),
    'widget.test_plan.Drawing.test_escape_cancels_the_outline':
        ('test_tools_parity.DrawingParity.test_measure_and_escape_three_levels',
         'Esc svuota il numero, poi la bozza, poi esce; eventi reali su entrambe le viste.'),
    'widget.test_plan.Drawing.test_escape_with_nothing_in_hand_leaves_the_tool':
        ('test_tools_parity.DrawingParity.test_measure_and_escape_three_levels',
         'Stesso strumento finale verificato dopo il terzo Esc.'),
    'widget.test_plan.Drawing.test_a_typed_length_and_turn':
        ('test_tools_parity.DrawingParity.test_building_vertices_numbers_and_rectangle',
         '10;90 e 5;90 digitati; confronto geometria e snapshot.'),
    'widget.test_plan_background.Fallback.test_failed_tiles_are_replaced_the_source_rests_and_retry_does_not_change_the_choice':
        ('test_maps.MapStateTests.test_three_distinct_current_failures_fallback_cooldown_retry_and_choice; '
         'test_maps.LoaderTests.test_xml_failure_retries_then_falls_back_and_keeps_the_saved_choice',
         'Tre guasti distinti, ripiego, cooldown, riprova e scelta salvata; HTTP locale reale.'),
    'widget.test_plan_background.Fallback.test_old_tiles_stay_until_the_new_view_is_covered':
        ('test_maps.MapStateTests.test_old_tiles_stay_until_full_new_coverage_and_none_clears',
         'Conservazione delle tessere fino alla copertura completa e cancellazione con Nessuno.'),
    'widget.test_plan_background.Fallback.test_an_xml_error_document_instead_of_an_image_also_uses_the_fallback':
        ('test_maps.LoaderTests.test_xml_failure_retries_then_falls_back_and_keeps_the_saved_choice',
         'Server HTTP locale risponde XML invece di PNG, retry reale e passaggio a seconda fonte.'),
    'widget.test_plan_background.Fallback.test_automatic_uses_the_street_map_afar_the_photo_near_and_never_overrides_a_manual_choice':
        ('test_maps.MapStateTests.test_automatic_near_far_manual_and_unknown_source; '
         'test_maps.MapStateTests.test_old_tiles_stay_until_full_new_coverage_and_none_clears',
         'Automatica stradale/ortofoto, manuale conservata e attribuzione della nuova fonte.'),
    'widget.test_plan_aids.PlanAids.test_a_source_this_version_does_not_know_falls_back_to_the_best_for_the_site':
        ('test_maps.MapStateTests.test_automatic_near_far_manual_and_unknown_source',
         'Fonte sconosciuta: automatica effettiva senza riscrivere la scelta.'),
    'widget.test_plan_aids.PlanAids.test_equal_earth_hides_tiles_without_loading_them_and_has_a_quiet_threshold':
        ('test_maps.MapStateTests.test_equal_earth_hysteresis_no_requests_and_all_countries_offline; '
         'test_maps.LoaderTests.test_quick_world_draws_country_pixels_and_labels_at_a_real_window',
         'Isteresi 2000/1500, richieste vuote, mondo QML renderizzato con attribuzione e sito.'),
}

PARTIAL = {
    'widget.test_tile_loader.TileCache.test_a_cached_tile_is_decoded_off_the_thread_and_offline_is_respected':
        ('test_maps.LoaderTests.test_cached_tile_is_async_deduplicated_offline_and_has_exact_pixels',
         'Portati thread, deduplicazione, pixel e offline; manca il caso file cache corrotto.'),
    'widget.test_tile_loader.DesignersSource.test_the_key_from_the_keyring_goes_in_the_address_only_with_the_user_agent_and_a_folder_of_its_own':
        ('test_maps.LoaderTests.test_custom_key_never_enters_cache_or_errors_and_missing_key_sends_nothing; '
         'test_maps.LoaderTests.test_xml_failure_retries_then_falls_back_and_keeps_the_saved_choice',
         'Portati chiave, cache con digest, oscuramento, User-Agent e retry; da asserire il conteggio unico del keyring.'),
    'widget.test_tile_loader.DesignersSource.test_without_a_key_or_with_the_servers_off_nothing_is_asked':
        ('test_maps.LoaderTests.test_custom_key_never_enters_cache_or_errors_and_missing_key_sends_nothing',
         'Chiave vuota verificata; manca la specifica eccezione KeyringMissing e fonte rimossa.'),
    'widget.test_plan_aids.PlanAids.test_natural_earth_draws_offline_alone_and_under_the_tiles':
        ('test_maps.LoaderTests.test_quick_world_draws_country_pixels_and_labels_at_a_real_window',
         'Portati mondo senza rete, riempimenti, nomi non sovrapposti, sito; manca il confronto sotto tessere regionali.'),
    'widget.test_plan_aids.PlanAids.test_the_source_of_the_background_is_said_only_over_a_background':
        ('test_maps.MapStateTests.test_old_tiles_stay_until_full_new_coverage_and_none_clears',
         'Stringa di attribuzione e Nessuno verificati; da confrontare la geometria del controllo a tutte le larghezze.'),
    'widget.test_plan.Drawing.test_a_rectangle_by_three_clicks':
        ('test_tools.test_rectangle_typed_depth_respects_pointer_side; '
         'test_tools_parity.DrawingParity.test_building_vertices_numbers_and_rectangle',
         'Parita numerica e backend; manca la sequenza completa dei tre click reali nel Quick.'),
    'widget.test_plan.Drawing.test_a_small_rectangle_closes_beside_an_edge':
        ('test_tools.test_rectangle_near_baseline_uses_unsnapped_depth',
         'Caso di regressione nel backend; da portare evento Qt e punto scena effettivo.'),
    'widget.test_plan.Drawing.test_shift_keeps_the_direction':
        ('test_tools.test_shift_locks_direction_until_released',
         'Vincolo nel backend; manca la pressione e il rilascio Shift sul QQuickWindow.'),
    'widget.test_plan.PlanNavigation.test_two_taps_select_the_row_and_escape_goes_to_the_container':
        ('test_edit_parity.WidgetsParity.test_module_row_parent_selection',
         'Gerarchia confrontata con eventi Widgets e intento backend; mancano i tap inviati a QQuickWindow.'),
    'widget.test_plan.PlanNavigation.test_escape_leaves_a_module_for_its_subfield':
        ('test_edit_parity.WidgetsParity.test_module_row_parent_selection',
         'Gerarchia del backend confrontata; manca Esc dalla selezione modulo nel QQuickWindow.'),
    'widget.test_plan.Moving.test_a_value_typed_moves_by_it_east_and_north':
        ('test_edit_parity.WidgetsParity.test_typed_move_and_rotation_commands',
         'Snapshot identico per 3;2, con input Widgets e backend Quick; adattatore Qt Quick da verificare.'),
    'widget.test_plan.Turning.test_an_angle_typed_and_enter':
        ('test_edit_parity.WidgetsParity.test_typed_move_and_rotation_commands',
         'Snapshot identico per 90 gradi; adattatore Qt Quick da verificare.'),
}

NOT_APPLICABLE = {
    'widget.test_plan_groups.TheGroups.test_a_group_kept_by_python_does_not_outlive_its_scene_as_a_stale_wrapper':
        'Dettaglio QGraphicsItemGroup/QGraphicsScene assente in Qt Quick. La vita dei nodi QSG richiede prove proprie.',
    'widget.test_plan_groups.TheGroups.test_the_plan_makes_no_group_in_c_plus_plus':
        'Controlla esclusivamente QGraphicsItemGroup, non usato dal Quick.',
}

# Additional contracts completed after the initial inventory. Keep partial entries explicit.
REPLACEMENTS.update({
    'widget.test_tile_loader.TileCache.test_a_cached_tile_is_decoded_off_the_thread_and_offline_is_respected':
        ('test_maps.LoaderTests.test_cached_tile_is_async_deduplicated_offline_and_has_exact_pixels; '
         'test_maps.LoaderTests.test_corrupt_cache_requests_image_online_and_offline_never_asks',
         'Thread decoder distinto, cache isolata, pixel e cache corrotta online/offline.'),
    'widget.test_tile_loader.TileCache.test_turning_offline_stops_a_queue_not_yet_sent':
        ('test_maps.LoaderTests.test_offline_stops_pending_queue_and_a_destroyed_loader_cancels_retry',
         'Coda annullata offline senza richiesta al server locale.'),
    'widget.test_tile_loader.Retry.test_a_loader_destroyed_before_the_retry_gets_no_late_call':
        ('test_maps.LoaderTests.test_offline_stops_pending_queue_and_a_destroyed_loader_cancels_retry',
         'Distruzione prima del timer: nessuna chiamata tardiva.'),
    'widget.test_tile_loader.DesignersSource.test_the_key_from_the_keyring_goes_in_the_address_only_with_the_user_agent_and_a_folder_of_its_own':
        ('test_maps.LoaderTests.test_custom_key_never_enters_cache_or_errors_and_missing_key_sends_nothing; '
         'test_maps.LoaderTests.test_xml_failure_retries_then_falls_back_and_keeps_the_saved_choice',
         'Keyring chiamato una volta, retry reale, UA, chiave oscurata ed esclusa dal percorso cache con digest.'),
    'widget.test_tile_loader.DesignersSource.test_without_a_key_or_with_the_servers_off_nothing_is_asked':
        ('test_maps.LoaderTests.test_missing_keyring_and_removed_source_send_no_requests; '
         'test_maps.LoaderTests.test_custom_key_never_enters_cache_or_errors_and_missing_key_sends_nothing',
         'KeyringMissing, chiave vuota, offline e fonte rimossa non inviano richieste.'),
    'widget.test_plan_background.Fallback.test_a_fallback_is_for_the_same_purpose_and_never_sentinel_close_up':
        ('test_maps.MapStateTests.test_fallback_never_substitutes_sentinel_for_a_detailed_orthophoto',
         'Ripiego rispetta risoluzione e finalita delle fonti.'),
    'widget.test_compass_layout.CompassLayout.test_the_centre_dot_is_fixed_while_the_letter_turns_with_the_arrow':
        ('test_aids.AidsQuick.test_centre_stays_fixed_letter_follows_north_and_real_click_requests_reset',
         'Pixel centro e posizione N alle cinque rotazioni, scale 1 e 2.'),
    'widget.test_compass_layout.CompassLayout.test_corner_changes_animate_once_and_stop_at_the_latest_target':
        ('test_aids.AidsQuick.test_corner_change_animates_once_latest_target_wins_and_reduced_motion_is_immediate',
         'Animazione, target ripetuto, ultimo target e reduced motion.'),
    'widget.test_symbols.Symbols.test_the_sign_is_opaque_and_white_on_a_ground_of_one_tone':
        ('test_marks.SymbolsQuick.test_every_symbol_renders_its_geometry_at_actual_screen_density; '
         'test_marks.SymbolsQuick.test_dark_palette_uses_the_same_vector_paths_and_lighter_info_and_neutral',
         'Segni bianchi opachi, tinta uniforme, divieto con fori e diagonale senza giunta, palette scura.'),
    'widget.test_symbols.Symbols.test_a_mark_of_the_checks_is_its_symbol':
        ('test_marks.MarkRecords.test_levels_positions_counts_and_targets_keep_their_meaning; '
         'test_marks.SymbolsQuick.test_every_symbol_renders_its_geometry_at_actual_screen_density',
         'Livello fail usa stop; barra bianca e disco rosso renderizzati.'),
})
PARTIAL.update({
    'widget.test_plan_sweep_light.SweepSpeed.test_a_move_draws_only_what_came_or_went':
        ('test_selection_window.SelectionWindow.test_live_twenty_thousand_modules_shift_pixels_and_local_frame_times',
         'Maschera incrementale verificata anche sui pixel lontani dall ultima striscia; '
         'non ancora confrontato tutto il buffer con LitModules Widgets.'),
    'widget.test_plan_sweep_light.SweepSpeed.test_a_sweep_over_thousands_of_modules_moves_in_a_few_milliseconds':
        ('test_selection_window.SelectionWindow.test_live_twenty_thousand_modules_shift_pixels_and_local_frame_times',
         '20.000 moduli, query e frame misurati con zero Python pointer. Vincolo temporale completo '
         'ancora da verificare, numeri e condizioni nello stato maps e JSON di cattura.'),
    'finestra.test_r10_commands.Sweeps.test_left_to_right_takes_what_is_all_inside_right_to_left_what_it_touches_too':
        ('test_selection.SelectionParity.test_window_crossing_boundaries_concavity_and_self_intersecting_lassos_match_core; '
         'test_selection.SelectionParity.test_seeded_rotated_quads_match_core_for_many_lassos',
         'Preview JS confrontato con core anche su lazi concavi/autointersecanti; viaggio MainWindow non portato.'),
    'widget.test_symbols.Symbols.test_the_warning_is_as_wide_as_the_disc':
        ('test_marks.SymbolsQuick.test_warning_width_matches_disc_r330',
         'Expected failure ereditato dal core: SVG warning largo 56 px, disco 60 px a taglia 64; '
         'la vecchia prova misurava il parser approssimato, non i pixel SVG.'),
    'widget.test_symbols.Symbols.test_the_symbols_say_what_daniel_listed':
        ('test_marks.MarkRecords.test_symbols_have_core_geometry_and_opaque_signs_and_views_ignore_the_ui_theme',
         'Nomi, geometrie, livello e errore nome ignoto coperti; icone sistema condivise fuori pianta.'),
    'widget.test_symbols.Symbols.test_discard_is_a_bin_on_the_red_and_cancel_an_arrow_back_on_the_grey':
        ('test_marks.SymbolsQuick.test_every_symbol_renders_its_geometry_at_actual_screen_density',
         'Pixel cestino e freccia portati; resta il contratto del segno isolato nelle pillole.'),
    'widget.test_marks.Sharp.test_an_icon_is_painted_at_the_density_asked':
        ('test_marks.SymbolsQuick.test_every_symbol_renders_its_geometry_at_actual_screen_density',
         'Simboli QML vettoriali provati a scala 1 e 2 e taglie 20/40; servizio icone condiviso fuori pianta.'),
    'widget.test_plan_aids.PlanAids.test_the_scale_bar_follows_the_zoom_with_round_lengths':
        ('test_aids.AidsQuick.test_scale_has_round_lengths_cm_m_km_and_fixed_pixel_height',
         'Regola 1-2-5, cm/m/km e pixel confrontati col core; manca prova di zoom reale sulla barra montata.'),
    'widget.test_plan_aids.PlanAids.test_the_n_of_the_compass_goes_with_the_arrow_and_a_click_brings_north_up':
        ('test_aids.AidsQuick.test_centre_stays_fixed_letter_follows_north_and_real_click_requests_reset',
         'N ruotata e click reale con segnale provati; tooltip e reset della vista montata da verificare.'),
    'widget.test_plan.PlanNavigation.test_the_plan_pans_zooms_and_recentres_with_the_same_style':
        ('test_navigation_window.NavigationWindow.test_middle_click_and_drag_in_all_styles_keep_core_semantics; '
         'test_navigation.NavigationParity.test_all_style_gestures_clicks_thresholds_modifiers_and_doubles',
         '14 stili con middle click/drag reali e tutte gesture in QJSEngine; mancano confronti completi Widgets.'),
    'widget.test_plan.PlanNavigation.test_in_the_plan_left_then_right_pans_without_selecting_or_drawing':
        ('test_navigation_window.NavigationWindow.test_chord_release_never_selects_or_turns_into_a_new_drag_and_space_does_not_reach_python',
         'Corda reale e rilascio senza selezione provati; manca il caso strumento disegno attivo.'),
    'widget.test_plan.PlanNavigation.test_windows_precision_scrolling_pans_both_axes_and_native_rotation_does_nothing':
        ('test_navigation_window.NavigationWindow.test_real_wheel_pixel_phase_precision_device_and_ctrl_keep_anchor',
         'Identita TouchPad, delta, fase, Ctrl e ancoraggio provati. QML non espone source() per evento sintetizzato '
         'con device mouse; gesture native non portate da questa prova.'),
})
for _key, (_replacement, _reason) in list(PARTIAL.items()):
    PARTIAL[_key] = (_replacement.replace('test_tools.test_', 'test_tools.DrawingTest.test_'), _reason)

for _name, _tests in {
    'test_native_pinch_two_finger_scroll_and_ctrl_scroll_drive_the_plan':
        'test_native_pinch_keeps_anchor_and_native_rotation_is_ignored; '
        'test_real_wheel_pixel_phase_precision_device_and_ctrl_keep_anchor',
    'test_wayland_scroll_phases_follow_both_fingers_without_changing_scale':
        'test_scroll_begin_update_end_moves_both_axes_without_zoom',
    'test_native_and_windows_pinches_keep_the_scene_point_under_the_cursor':
        'test_native_pinch_keeps_anchor_and_native_rotation_is_ignored; '
        'test_real_wheel_pixel_phase_precision_device_and_ctrl_keep_anchor',
    'test_space_alone_follows_the_mouse_and_windows_auto_repeat_does_not_release_it':
        'test_space_auto_repeat_and_chord_leave_a_drawing_untouched',
}.items():
    REPLACEMENTS['widget.test_plan.PlanNavigation.'+_name] = (
        '; '.join('test_navigation_window.NavigationWindow.'+test for test in _tests.split('; ')),
        'Eventi Qt nativi sulla finestra Quick, ancoraggio e delta asseriti; nessun Python pointer.')

for _name in ('test_passing_over_a_grip_says_what_it_does_with_the_cursor_and_the_status_bar',
              'test_the_grips_are_round_with_their_icon_and_take_the_whole_disc',
              'test_during_a_gesture_the_grips_keep_quiet'):
    REPLACEMENTS['widget.test_plan.Grips.'+_name] = (
        'test_edit_window.EditWindowTest.test_grip_hover_cursor_disc_reach_and_active_gesture; '
        'test_edit_window.EditWindowTest.test_transform_grip_drag_ctrl_release_then_hot_cycle',
        'Hover reale, cursore Bitmap per Ruota, stesso testo, disco e angoli fuori presa, disabilitata durante gesto.')

for _old, _new in {
    'Modules.test_the_modules_stay_while_their_layout_is_the_same':
        'test_renaming_and_camera_changes_retain_native_module_paths',
    'Sides.test_a_side_is_picked_with_a_click':
        'test_edge_collection_hover_cancel_and_short_side_without_pill',
    'Turning.test_turning_a_sub_field_by_30_degrees_writes_30_and_asks_for_30':
        'test_rotation_card_matches_the_committed_angle_and_copy',
    'Turning.test_c_copies_a_turn':
        'test_rotation_card_matches_the_committed_angle_and_copy',
    'Turning.test_the_rotate_button_starts_turning_the_next_object_picked':
        'test_rotate_before_picking_and_move_distance_card',
}.items():
    REPLACEMENTS['widget.test_plan.'+_old] = ('test_contracts.Contracts.'+_new,
        'Finestra Quick nativa: progetto risultante, scheda, raccolta lato e riuso geometria verificati.')
REPLACEMENTS['widget.test_plan.Sides.test_a_short_side_gets_its_number_alone_or_nothing_and_the_field_still_opens'] = (
    'test_contracts.Contracts.test_edge_collection_hover_cancel_and_short_side_without_pill; '
    'test_edit_window.EditWindowTest.test_side_pills_notch_outside_nonoverlap_and_widgets_geometry',
    'Stesse pillole dei Widgets, tacca, numero solo, nessuna sovrapposizione e campo aperto anche senza pillola.')


for _old, _new in {
    'widget.test_compass_layout.CompassLayout.test_the_compass_moves_below_the_tools_and_returns_when_room_is_available':
        'test_compass_scale_corners_pan_resize_and_toolbar_avoidance',
    'widget.test_plan_aids.PlanAids.test_the_north_arrow_and_the_scale_bar_sit_in_their_corners_over_the_viewport':
        'test_compass_scale_corners_pan_resize_and_toolbar_avoidance',
    'widget.test_plan_aids.PlanAids.test_the_north_arrow_and_the_scale_bar_stay_put_while_the_plan_moves':
        'test_compass_scale_corners_pan_resize_and_toolbar_avoidance',
    'widget.test_plan_aids.PlanAids.test_the_scale_bar_follows_the_zoom_with_round_lengths':
        'test_real_zoom_scale_rotate_pan_and_compass_reset_preserve_project',
    'widget.test_plan_aids.PlanAids.test_string_numbers_stay_on_their_modules_at_every_rotation_zoom_and_pan':
        'test_string_numbers_and_eight_pixel_dots_follow_modules_at_all_camera_transforms',
    'widget.test_plan_aids.PlanAids.test_every_stringed_module_has_a_screen_sized_dot_until_modules_get_small':
        'test_string_numbers_and_eight_pixel_dots_follow_modules_at_all_camera_transforms',
    'widget.test_plan_aids.PlanAids.test_the_n_of_the_compass_goes_with_the_arrow_and_a_click_brings_north_up':
        'test_real_zoom_scale_rotate_pan_and_compass_reset_preserve_project',
    'widget.test_side_field.SideField.test_the_field_stands_in_the_pill_in_its_measures':
        'test_side_field_pill_disc_font_and_baseline_at_two_zoom_levels',
    'widget.test_side_field.SideField.test_and_so_at_another_zoom':
        'test_side_field_pill_disc_font_and_baseline_at_two_zoom_levels',
}.items():
    REPLACEMENTS[_old] = ('test_aids_window.AidsWindow.'+_new,
        'Prova sulla pianta montata: coordinate, camera, font, dimensioni e progetto invariato; eventi Qt dove richiesti.')
PARTIAL['widget.test_plan_aids.PlanAids.test_the_plan_rotates_without_changing_the_project_and_the_compass_follows'] = (
    'test_aids_window.AidsWindow.test_real_zoom_scale_rotate_pan_and_compass_reset_preserve_project',
    'Rotazione, centro, pan ruotato, scala, progetto e clic Nord provati; manca il confronto allinea al lato Widgets.')
REPLACEMENTS['widget.test_plan.PlanNavigation.test_in_the_plan_left_then_right_pans_without_selecting_or_drawing'] = (
    'test_navigation_window.NavigationWindow.test_space_auto_repeat_and_chord_leave_a_drawing_untouched; '
    'test_navigation_window.NavigationWindow.test_chord_release_never_selects_or_turns_into_a_new_drag_and_space_does_not_reach_python',
    'Corda di pulsanti provata sia durante il disegno sia in selezione, con rilascio e nessun comando spurio.')


def inventory():
    from quick.pianta.test_edit_mapping import EDIT_MAPPING
    from quick.pianta.test_tools_mapping import TOOLS_MAPPING
    for key, item in {**EDIT_MAPPING, **TOOLS_MAPPING}.items():
        target = REPLACEMENTS if item['status'] == 'fatto' else PARTIAL
        # A newer, stronger assertion in this file takes precedence.
        if key not in REPLACEMENTS:
            target[key] = (item['quick_replacement'].replace('quick.pianta.', ''), item['notes'])
    registry_path = ROOT / 'docs/quick/compat/prove.csv'
    with registry_path.open(encoding='utf-8-sig', newline='') as stream:
        registry = {row['test']: row for row in csv.DictReader(stream)}
    rows = []
    for group in ('widget', 'finestra'):
        for path in sorted((ROOT / 'tests' / group).glob('test_*.py')):
            text = path.read_text(encoding='utf-8-sig')
            if not MATCH.search(text):
                continue
            for cls in ast.parse(text).body:
                if not isinstance(cls, ast.ClassDef):
                    continue
                for node in cls.body:
                    if not isinstance(node, ast.FunctionDef) or not node.name.startswith('test_'):
                        continue
                    key = f'{group}.{path.stem}.{cls.name}.{node.name}'
                    if key not in registry:
                        raise ValueError(f'Test absent from the shared compatibility inventory: {key}')
                    status, replacement = 'da portare', ''
                    reason = 'Nessuna prova Quick completa identificata; conservare gli assert del metodo.'
                    if key in REPLACEMENTS:
                        status = 'sostituita'
                        replacement, reason = REPLACEMENTS[key]
                    elif key in PARTIAL:
                        replacement, reason = PARTIAL[key]
                    elif key in NOT_APPLICABLE:
                        status, reason = 'non valida', NOT_APPLICABLE[key]
                    elif path.stem == 'test_map_sources':
                        reason = ('Pagina Impostazioni Mappe fuori da questo ramo. Il controller riusa tiles.catalogue, '
                                  'ma editor fonti, capabilities, licenze e keyring UI non sono portati.')
                    elif path.stem in ('test_marks', 'test_symbols'):
                        reason = ('Icone, albero e simboli condivisi: parte UI da coordinare con sistema; '
                                  'nessuna equivalenza dedotta dalla sola presenza del simbolo nel Quick.')
                    elif group == 'finestra':
                        reason = ('Viaggio MainWindow completo: anche dove il backend e portato, mancano '
                                  'pannelli, menu o controllo incrociato delle viste richiesti dal metodo.')
                    rows.append(dict(test=key, source=f'{path.relative_to(ROOT).as_posix()}:{node.lineno}',
                                     status=status, replacement=replacement, reason=reason))
    return rows


def render(rows):
    counts = Counter(row['status'] for row in rows)
    text = [
        '# Inventario delle prove della pianta Quick', '', 'Data: 05/11/2026.', '',
        '[V] Metodi e identificatori ricavati da AST e confrontati con `docs/quick/compat/prove.csv`.',
        '[V] Selezione per import/nome: plan, PlanView, plan_view, plan_overlays, lit_modules, marks, symbols, '
        'tileloader, world_map e map_sources. Sono inclusi tutti i metodi dei moduli che li citano, anche quelli '
        'di altre aree: il perimetro e volutamente conservativo.',
        '[I] Le assegnazioni alle prove sostitutive sono letture dei relativi assert, non un certificato di '
        'esecuzione. Gli esiti effettivi stanno negli stati degli agenti e nei log dei giri.', '',
        f'Totale: {len(rows)} metodi. ' + '; '.join(f'{key}: {counts[key]}' for key in sorted(counts)) + '.', '',
        '- `sostituita`: contratto osservabile coperto dai metodi Quick indicati, con struttura diversa.',
        '- `da portare`: prova assente o copertura parziale, indicata esplicitamente.',
        '- `non valida`: solo dettagli QGraphics assenti nel Quick, con motivo specifico.',
        '- Nessun metodo e dichiarato `portata`: non sono copie uno a uno della prova Widgets.', '',
        'Rigenerare: `python tests/quick/pianta/inventory.py` con `PYTHONPATH=src;tests`.', '',
        '| Metodo Widgets | Stato | Prova Quick e motivo |', '|---|---|---|',
    ]
    for row in rows:
        evidence = f"`{row['replacement']}`. " if row['replacement'] else ''
        text.append(f"| `{row['test']}` | {row['status']} | {evidence}{row['reason']} |")
    return '\n'.join(text) + '\n'


if __name__ == '__main__':
    entries = inventory()
    destination = ROOT / 'docs/quick/stato/pianta-prove.md'
    destination.write_text(render(entries), encoding='utf-8')
    print(f'{len(entries)} methods: {dict(Counter(row["status"] for row in entries))}')
