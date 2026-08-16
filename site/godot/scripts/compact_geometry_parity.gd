extends "res://scripts/geometry_parity.gd"

# Tablet/compact topology keeps the desktop navigation shell, but side-by-side
# evidence surfaces must stop competing with editorial copy as width contracts.
# Reuse the existing phone evidence primitives inside the compact hero instead
# of inventing a second visual language or viewport-specific scale transform.

func _build() -> void:
	super._build()
	if _layout != "compact":
		return
	match _current_route():
		"/architecture": _patch_architecture_compact()
		"/publication":
			if size.x >= 900.0:
				_patch_publication_wide_compact()
		"/playground": _patch_playground_compact()
		"/agents": _patch_agents_compact()
		"/changelog": _patch_changelog_compact()

func _patch_architecture_compact() -> void:
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var target_height := 1020.0 if _locale == "en-US" else 980.0
	var delta := target_height - hero.size.y
	_resize_hero(hero, target_height, 8.0)
	var project_label := _find_label_exact(hero, "Project")
	if project_label != null and project_label.get_parent() != null and project_label.get_parent().get_parent() is Control:
		var grid := project_label.get_parent().get_parent() as Control
		var parent := grid.get_parent()
		parent.remove_child(grid)
		grid.free()
		var grid_y := 455.0 if _locale == "en-US" else 420.0
		_build_architecture_grid(hero, Vector2(44.0, grid_y), Vector2(hero.size.x - 88.0, 520.0), true)
	_shift_stage_controls(650.0, delta, hero)
	_stage.custom_minimum_size.y += delta

func _patch_publication_wide_compact() -> void:
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var target_height := 860.0 if _locale == "en-US" else 770.0
	var delta := target_height - hero.size.y
	_resize_hero(hero, target_height, 8.0)
	var epub_tag := _find_negative_y_label(hero, "EPUB")
	if epub_tag != null and epub_tag.get_parent() != null and epub_tag.get_parent().get_parent() is Control:
		var epub_card := epub_tag.get_parent().get_parent() as Control
		if epub_card.get_parent() is Control:
			var showcase := epub_card.get_parent() as Control
			var parent := showcase.get_parent()
			parent.remove_child(showcase)
			showcase.free()
			var showcase_y := 535.0 if _locale == "en-US" else 445.0
			_build_format_showcase(hero, Vector2(44.0, showcase_y), Vector2(hero.size.x - 88.0, 280.0), false)
	_shift_stage_controls(700.0, delta, hero)
	_stage.custom_minimum_size.y += delta

func _patch_playground_compact() -> void:
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var target_height := 920.0 if _locale == "en-US" else 820.0
	var delta := target_height - hero.size.y
	_resize_hero(hero, target_height, 8.0)
	var draft := _find_label_exact(hero, "DRAFT")
	if draft != null and draft.get_parent() != null and draft.get_parent().get_parent() != null and draft.get_parent().get_parent().get_parent() is Control:
		var row := draft.get_parent() as Control
		var inner := row.get_parent() as Control
		var canvas := inner.get_parent() as Control
		var parent := canvas.get_parent()
		parent.remove_child(canvas)
		canvas.free()
		var preview_y := 510.0 if _locale == "en-US" else 410.0
		_build_trace_preview(hero, Vector2(48.0, preview_y), Vector2(hero.size.x - 96.0, 350.0), true)
	_shift_stage_controls(680.0, delta, hero)
	_stage.custom_minimum_size.y += delta

func _patch_agents_compact() -> void:
	var hero := _find_stage_panel(110.0, 520.0)
	if hero == null:
		return
	var target_height := 990.0 if _locale == "en-US" else 920.0
	var delta := target_height - hero.size.y
	_resize_hero(hero, target_height, 8.0)
	var bay_label := _find_label_exact(hero, "AGENT PATCH BAY")
	if bay_label != null and bay_label.get_parent() is Control:
		var bay := bay_label.get_parent() as Control
		var parent := bay.get_parent()
		parent.remove_child(bay)
		bay.free()
		var bay_y := 500.0 if _locale == "en-US" else 430.0
		_build_agent_patch_bay(hero, Vector2(48.0, bay_y), Vector2(hero.size.x - 96.0, 430.0), true)
	for child in hero.get_children():
		if child is Label and (child as Label).text == "Host Bridge · authority=false":
			var signature := child as Label
			signature.position = Vector2(hero.size.x - 230.0, target_height - 48.0)
	_shift_stage_controls(690.0, delta, hero)
	_stage.custom_minimum_size.y += delta

func _patch_changelog_compact() -> void:
	var hero := _find_stage_panel(110.0, 480.0)
	if hero == null:
		return
	var target_height := 720.0 if _locale == "en-US" else 630.0
	var delta := target_height - hero.size.y
	_resize_hero(hero, target_height, 8.0)
	var version := _find_label_exact(hero, "0.8.x")
	if version != null and version.get_parent() is Control:
		var oval := version.get_parent() as Control
		var parent := oval.get_parent()
		parent.remove_child(oval)
		oval.free()
		var oval_y := 480.0 if _locale == "en-US" else 390.0
		_build_release_oval(hero, Vector2(48.0, oval_y), Vector2(hero.size.x - 96.0, 180.0))
	_shift_stage_controls(650.0, delta, hero)
	_stage.custom_minimum_size.y += delta
