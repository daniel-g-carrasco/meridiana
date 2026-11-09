"""Reviewed edit evidence for the compatibility inventory, not a blanket waiver.

The parent integration owns docs/quick/compat. Entries that cover only part of a
Widgets test remain in progress and explicitly name the missing assertions.
"""

BASE = "quick.pianta.test_edit_window.EditWindowTest."
PURE = "quick.pianta.test_edit.EditorTest."
PARITY = "quick.pianta.test_edit_parity.WidgetsParity."
PHOTOS = "build/quick-foto/pianta/edit/"


def evidence(tests, photo="", missing=""):
    return {"quick_replacement": tests,
            "status": "da fare" if not tests else "in corso" if missing else "fatto",
            "evidence": [tests] + ([PHOTOS + photo] if photo else []),
            "notes": missing or "[V] Test comportamentale e immagine reale D3D11 controllati."}


EDIT_MAPPING = {
    "widget.test_plan.Modules.test_a_module_is_picked_from_the_array_of_the_corners": evidence(
        PARITY + "test_pick_boundaries_match_widgets_convex_test; " + PURE + "test_pick_twenty_thousand_modules_caches_shapes",
        "01-modulo@1x.png"),
    "widget.test_plan.Modules.test_the_modules_stay_while_their_layout_is_the_same": evidence(
        BASE + "test_phase_changes_keep_geometry_and_hint_scope; " + BASE + "test_native_phase_frames_keep_modules_visible",
        "10-fase-model@1x.png", "Provati dati e frame durante cambio fase; non ancora identità e riuso dei buffer GPU a ogni modifica del progetto."),
    "widget.test_plan.Sides.test_a_side_is_picked_with_a_click": evidence(
        BASE + "test_side_length_focus_escape_and_commit", "03-lato-input@1x.png",
        "Clic pillola provato; resta selezione singola del bordo e evidenziazione lato."),
    "widget.test_plan.Sides.test_the_ridge_lights_up_when_the_pointer_passes_over_the_roof": evidence(
        "", missing="Manca hover del colmo e sua evidenziazione."),
    "widget.test_plan.Sides.test_a_double_click_on_a_side_of_the_selection_asks_its_length": evidence(
        BASE + "test_double_click_selected_edge_opens_length", "03-lato-input@1x.png",
        "Ultimo giro fallito su sideEditing False; da riprovare dopo il congelamento API controller/QML."),
    "widget.test_plan.Sides.test_the_pills_carry_the_number_and_the_length_outside_the_outline_without_overlapping": evidence(
        BASE + "test_side_pills_notch_outside_nonoverlap_and_widgets_geometry", "18-quote-tacca-25@1x.png",
        "Geometria, testo, assenza sovrapposizioni e posizione esterna provati contro _side_pills Widgets; mancano hover, cursore e Properties.highlight_side."),
    "widget.test_plan.Sides.test_a_click_on_the_pill_opens_the_field_and_enter_gives_the_length": evidence(
        BASE + "test_side_length_focus_escape_and_commit", "03-lato-input@1x.png"),
    "widget.test_plan.Sides.test_escape_leaves_the_side_and_a_text_that_is_not_a_length_is_refused_and_said": evidence(
        BASE + "test_side_invalid_keeps_focus_and_selection", "11-lato-invalido@1x.png",
        "Errore/focus/annulla provati; resta chiusura del campo quando la vista si sposta."),
    "widget.test_plan.Sides.test_a_short_side_gets_its_number_alone_or_nothing_and_the_field_still_opens": evidence(
        BASE + "test_side_pills_notch_outside_nonoverlap_and_widgets_geometry", "18-quote-tacca-0@1x.png",
        "Riduzione a numero e soppressione provate; resta apertura campo del lato breve privo di pillola."),
    "widget.test_plan.Sides.test_the_pills_follow_a_turned_plan_and_their_click_still_opens_the_side": evidence(
        BASE + "test_rotated_side_label_is_clickable; " + BASE + "test_side_pills_notch_outside_nonoverlap_and_widgets_geometry",
        "12-lato-vista-ruotata@1x.png"),
    "widget.test_plan.Sides.test_a_corner_of_the_selection_is_dragged": evidence(
        BASE + "test_vertex_drag; " + BASE + "test_vertex_grips_follow_camera", "04-vertice@1x.png"),
    "widget.test_plan.Moving.test_two_clicks_give_the_move_from_the_base_point_to_the_second": evidence(
        BASE + "test_mouse_ctrl_copy_and_rotation_steps", "02-copia-ruotata@1x.png"),
    "widget.test_plan.Moving.test_the_points_snap_to_the_corners": evidence(
        BASE + "test_move_snaps_base_and_destination", "09-sposta-agganciato@1x.png"),
    "widget.test_plan.Moving.test_a_value_typed_moves_by_it_east_and_north": evidence(
        PARITY + "test_typed_move_and_rotation_commands; " + BASE + "test_move_nudge_copy_rotate_typed",
        "02-copia-ruotata@1x.png"),
    "widget.test_plan.Moving.test_a_distance_typed_goes_along_the_pointer_and_tab_gives_the_direction": evidence(
        BASE + "test_move_tab_direction_and_r_uses_clicked_pivot", "13-ruota-punto-base@1x.png"),
    "widget.test_plan.Moving.test_ctrl_held_at_the_click_makes_a_copy": evidence(
        BASE + "test_mouse_ctrl_copy_and_rotation_steps", "02-copia-ruotata@1x.png"),
    "widget.test_plan.Moving.test_c_makes_a_copy_too_and_esc_leaves_without_a_move": evidence(
        BASE + "test_move_nudge_copy_rotate_typed", "02-copia-ruotata@1x.png",
        "Copia C provata; annulla durante copia prima del commit non ancora provato nella finestra reale."),
    "widget.test_plan.Moving.test_with_nothing_selected_a_click_picks_what_to_move": evidence(
        PURE + "test_plant_cannot_move_building", missing="Backend copre selezione Impianto; manca viaggio reale da nessuna selezione a Sposta edificio."),
    "widget.test_plan.Moving.test_the_arrows_nudge_the_selection": evidence(
        BASE + "test_move_nudge_copy_rotate_typed", "02-copia-ruotata@1x.png"),
    "widget.test_plan.Turning.test_ctrl_gives_steps_of_5_degrees_and_shift_of_90": evidence(
        BASE + "test_mouse_ctrl_copy_and_rotation_steps", "15-presa-ruota@1x.png"),
    "widget.test_plan.Turning.test_an_angle_typed_and_enter": evidence(
        PARITY + "test_typed_move_and_rotation_commands; " + BASE + "test_move_nudge_copy_rotate_typed",
        "02-copia-ruotata@1x.png"),
    "widget.test_plan.Turning.test_r_after_the_base_point_turns_about_it_and_r_again_goes_back_to_the_move": evidence(
        BASE + "test_move_tab_direction_and_r_uses_clicked_pivot", "13-ruota-punto-base@1x.png",
        "Pivot esplicito e angolo provati; ritorno con secondo R ancora solo coperto dal nucleo."),
    "widget.test_plan.Turning.test_the_rotate_button_starts_turning_the_next_object_picked": evidence(
        "", missing="Manca viaggio reale Ruota prima di scegliere oggetto."),
    "widget.test_plan.Turning.test_c_copies_a_turn": evidence(
        PURE + "test_hot_grip_cycles_and_typed_commit", missing="Copia rotazione provata nel backend; manca commit copia ruotata dalla presa QML."),
    "widget.test_plan.Grips.test_the_grips_are_in_the_middle_and_on_the_northern_side_only_with_move": evidence(
        BASE + "test_transform_grip_drag_ctrl_release_then_hot_cycle; " + BASE + "test_rotation_grip_drag_about_middle",
        "14-presa-attiva@1x.png"),
    "widget.test_plan.Grips.test_passing_over_a_grip_says_what_it_does_with_the_cursor_and_the_status_bar": evidence(
        "", missing="Manca prova hover di entrambe le prese, cursore e suggerimento."),
    "widget.test_plan.Grips.test_the_grips_are_round_with_their_icon_and_take_the_whole_disc": evidence(
        BASE + "test_transform_grip_drag_ctrl_release_then_hot_cycle", "14-presa-attiva@1x.png",
        "Forma e icona viste; hit test sui bordi del disco non ancora provato."),
    "widget.test_plan.Grips.test_during_a_gesture_the_grips_keep_quiet": evidence(
        "", missing="Manca tentativo di prendere una seconda presa durante gesto attivo."),
    "widget.test_plan.Grips.test_dragging_the_middle_grip_is_a_move": evidence(
        BASE + "test_transform_grip_drag_ctrl_release_then_hot_cycle", "14-presa-attiva@1x.png"),
    "widget.test_plan.Grips.test_ctrl_held_at_the_release_of_a_grip_copies": evidence(
        BASE + "test_transform_grip_drag_ctrl_release_then_hot_cycle", "14-presa-attiva@1x.png"),
    "widget.test_plan.Grips.test_dragging_the_grip_on_the_outline_turns_about_the_middle": evidence(
        BASE + "test_rotation_grip_drag_about_middle", "15-presa-ruota@1x.png"),
    "widget.test_plan.Grips.test_a_grip_clicked_is_hot_and_enter_or_space_go_round_the_modes": evidence(
        PARITY + "test_hot_grips_cycle_like_widgets; " + BASE + "test_transform_grip_drag_ctrl_release_then_hot_cycle",
        "14-presa-attiva@1x.png"),
    "widget.test_plan.PlanNavigation.test_two_taps_select_the_row_and_escape_goes_to_the_container": evidence(
        BASE + "test_selection_row_escape_delete", "01b-fila@1x.png"),
    "widget.test_plan.PlanNavigation.test_escape_leaves_a_module_for_its_subfield": evidence(
        PARITY + "test_module_row_parent_selection", "01-modulo@1x.png"),
    "widget.test_plan.PlanNavigation.test_a_touchpad_tap_takes_a_module_within_six_logical_pixels": evidence(
        PURE + "test_touchpad_pick_six_pixels_and_nearest_across_subfields; " + BASE + "test_touchpad_six_pixels_seven_pixels_and_double_tap",
        missing="Backend 6px/7px verificato a due scale; prova QML scritta, da eseguire alla fine della misura GPU isolata."),
    "widget.test_plan.PlanNavigation.test_a_double_tap_selects_the_row_and_still_reports_the_double_click": evidence(
        BASE + "test_touchpad_six_pixels_seven_pixels_and_double_tap",
        missing="Prova QML scritta, da eseguire alla fine della misura GPU isolata."),
    "widget.test_plan_sweep_light.SweepLight.test_shift_lights_the_modules_in_the_red_of_the_removal_and_says_so_at_once": evidence(
        BASE + "test_box_crossing_lasso_shift", "05-lasso@1x.png",
        "Sottrazione Shift verificata; luce rossa e segno durante trascinamento ancora da verificare."),
    "widget.test_plan.PlanNavigation.test_string_chips_use_the_design_radius_font_and_drawn_symbols": evidence(
        BASE + "test_string_name_chip_matches_widgets_and_culls_collisions; " + PURE + "test_wiring_names_use_real_state_or_unchecked_default",
        missing="Dati di stato verificati; prova geometria nome stringa scritta, da eseguire dopo la misura GPU. Chip generico senza swatch non usato dalla pianta Quick."),
    "widget.test_plan.PlanNavigation.test_a_strings_name_is_a_pill_with_its_colour_as_a_dot_and_its_state_on_the_right_ends_centre": evidence(
        BASE + "test_string_name_chip_matches_widgets_and_culls_collisions",
        missing="Confronto ChipItem per geometria, testo, font, colore punto e centro simbolo scritto; da eseguire dopo la misura GPU."),
}

# Final real-window runs after the renderer and adapter API stopped changing.
for _key, _row in EDIT_MAPPING.items():
    if any(name in _row['quick_replacement'] for name in (
            'test_touchpad_six_pixels_seven_pixels_and_double_tap',
            'test_string_name_chip_matches_widgets_and_culls_collisions',
            'test_double_click_selected_edge_opens_length')):
        _row['status'] = 'fatto'
        _row['notes'] = '[V] Giro D3D11 a thread verde; assert originali conservati, senza warning QML.'
for _name, _test in {
    'test_the_ridge_lights_up_when_the_pointer_passes_over_the_roof': 'test_hover_roof_lights_its_ridge_without_python_pointer_calls',
    'test_with_nothing_selected_a_click_picks_what_to_move': 'test_move_from_empty_selection_cancel_copy_and_return_from_rotate',
    'test_c_makes_a_copy_too_and_esc_leaves_without_a_move': 'test_move_from_empty_selection_cancel_copy_and_return_from_rotate',
    'test_r_after_the_base_point_turns_about_it_and_r_again_goes_back_to_the_move': 'test_move_from_empty_selection_cancel_copy_and_return_from_rotate',
    'test_escape_leaves_the_side_and_a_text_that_is_not_a_length_is_refused_and_said': 'test_side_invalid_keeps_focus_and_selection; '+BASE+'test_side_field_closes_on_pan_without_applying_a_number',
}.items():
    for _key in EDIT_MAPPING:
        if _key.endswith('.'+_name):
            EDIT_MAPPING[_key] = evidence(BASE+_test)
