extends "res://scripts/mobile_geometry_parity.gd"

# Final cross-viewport geometry bridge. Solid/Vite remains the screenshot
# authority; this layer only reproduces browser CSS flow where fixed Godot
# controls would otherwise change wrapping, hero height, or column geometry.

var _home_heading_fonts := {}
var _spaced_latin_fonts := {}

func _build() -> void:
	super._build()
	_patch_shared_symbol_fonts()
	_patch_home_typography()
	if _layout == "phone":
		match _current_route():
			"/architecture": _patch_architecture_phone()
			"/inspect": _patch_inspect_phone()
			"/playground": _patch_playground_phone()
		return
	if _layout == "compact":
		match _current_route():
			"/studio": _patch_studio_compact()
			"/architecture": _patch_architecture_compact()
			"/publication": _patch_publication_compact()
			"/inspect": _patch_inspect_compact()
			"/playground": _patch_playground_compact()
			"/agents": _patch_agents_compact()
			"/changelog": _patch_changelog_compact()
		return
	if _layout != "desktop":
		return
	match _current_route():
		"/product": _patch_product_desktop()
		"/studio": _patch_studio_desktop()
		"/architecture": _patch_architecture_desktop()

func _home_heading_font(spacing: int) -> Font:
	if _home_heading_fonts.has(spacing):
		return _home_heading_fonts[spacing]
	var variation := FontVariation.new()
	variation.base_font = _latin_base_font
	variation.spacing_glyph = spacing
	variation.spacing_space = spacing
	var text_server := TextServerManager.get_primary_interface()
	variation.variation_opentype = {text_server.name_to_tag("wght"): 810}
	_home_heading_fonts[spacing] = variation
	return variation

func _spaced_latin_font(weight: int, spacing: int) -> Font:
	var key := "%d:%d" % [weight, spacing]
	if _spaced_latin_fonts.has(key):
		return _spaced_latin_fonts[key]
	var variation := FontVariation.new()
	variation.base_font = _latin_base_font
	variation.spacing_glyph = spacing
	variation.spacing_space = spacing
	var text_server := TextServerManager.get_primary_interface()
	variation.variation_opentype = {text_server.name_to_tag("wght"): weight}
	_spaced_latin_fonts[key] = variation
	return variation

func _patch_home_typography() -> void:
	if _current_route() != "/" or _locale != "en-US":
		return
	var title := _find_label_prefix(self, "Let the story\ngrow without")
	if title != null:
		title.add_theme_font_override("font", _home_heading_font(-5 if _layout == "desktop" else -3))
		if _layout == "desktop":
			title.position.y = 202.0
	var lede := _find_label_prefix(self, "NovelForge connects creation")
	if lede != null and _layout == "phone":
		lede.add_theme_constant_override("line_spacing", 7)
		lede.add_theme_font_override("font", _spaced_latin_font(420, -1))

func _patch_shared_symbol_fonts() -> void:
	for symbol in ["◐", "≡", "☼"]:
		var button := _find_button_exact(self, symbol)
		if button != null:
			button.add_theme_font_override("font", _mixed_font(650))
	var search := _find_label_prefix(self, "⌕  Search")
	if search != null:
		search.add_theme_font_override("font", _mixed_font(430))
	var docs := _find_button_exact(self, "📚 Read architecture docs")
	if docs != null:
		# The button already owns the deterministic local books SVG as its icon.
		docs.text = "Read architecture docs"

func _patch_product_desktop() -> void:
	var hero := _find_stage_panel(122.0, 450.0)
	if hero == null:
		return
	_resize_hero(hero, 420.0, 8.0)
	var title := _find_label_prefix(hero, "NovelForge is a\nfiction production")
	if title != null:
		title.text = "NovelForge is a fiction\nproduction system,\nnot a prompt wrapper."
		title.position.y = 68.0
		title.size = Vector2(650.0, 190.0)
		title.add_theme_constant_override("line_spacing", -10)
	var lede := _find_label_prefix(hero, "It separates creative judgment")
	if lede != null:
		lede.text = "It separates creative judgment from deterministic control so a long-running\nbook can accumulate evidence, revisions, and state without turning every\nprevious model output into truth."
		lede.position.y = 288.0
		lede.size = Vector2(650.0, 102.0)
	var story_state := _find_label_exact(hero, "♡ STORY STATE")
	if story_state != null and story_state.get_parent() != null and story_state.get_parent().get_parent() is Control:
		var stack := story_state.get_parent().get_parent() as Control
		stack.size.y = 300.0
		var names := ["Canon", "Context", "Evidence", "Candidate", "Settlement"]
		for i in range(names.size()):
			var row_label := _find_label_exact(stack, str(names[i]))
			if row_label != null and row_label.get_parent() is Control:
				(row_label.get_parent() as Control).position.y = 33.0 + i * 54.0
	_shift_stage_controls(630.0, -65.0, hero)
	_stage.custom_minimum_size.y = max(_stage.custom_minimum_size.y - 65.0, 1040.0)

func _patch_studio_desktop() -> void:
	var hero := _find_stage_panel(122.0, 700.0)
	if hero == null:
		return
	_resize_hero(hero, 673.0, 8.0)
	var title := _find_label_prefix(hero, "The creative\nworkbench\naround Core —")
	if title != null:
		title.text = "The creative\nworkbench\naround Core —\nwith progressive\ndisclosure instead of\ndashboard overload."
		title.position.y = 68.0
		title.size = Vector2(620.0, 385.0)
	var lede := _find_label_prefix(hero, "Phase 2C now ships")
	if lede != null:
		lede.text = "Phase 2C now ships a real read-only SolidJS shell: bilingual, mobile-first,\nloopback-hosted, no default polling, and backed by the public Host Bridge.\nLocal Web remains first-class; Tauri is still optional."
		lede.position.y = 478.0
	var cta := _find_button_exact(hero, "✦ Open Hosted Studio")
	if cta != null:
		cta.position.y = 583.0
	var host := _find_label_exact(hero, "studio.novelforge.wei-dev.com")
	if host != null and host.get_parent() != null and host.get_parent().get_parent() is Control:
		var terminal := host.get_parent().get_parent() as Control
		terminal.position = Vector2(733.0, 224.0)
		terminal.size.x = 470.0
		for child in terminal.get_children():
			if child is Control:
				var control := child as Control
				if abs(control.position.y) < 1.0:
					control.size.x = 470.0
				elif control is Label:
					control.size.x = min(control.size.x, 420.0)
		host.size.x = 380.0
	var signature := _find_label_exact(hero, "✦ Studio ♡")
	if signature != null:
		signature.position.y = 603.0
	_shift_stage_controls(880.0, -65.0, hero)
	_stage.custom_minimum_size.y = max(_stage.custom_minimum_size.y - 65.0, 1080.0)

func _patch_studio_compact() -> void:
	var hero := _find_stage_panel(110.0, 700.0)
	if hero == null:
		return
	var target_height := 1040.0 if _locale == "en-US" else 930.0
	var delta := target_height - hero.size.y
	_resize_hero(hero, target_height, 8.0)
	var host := _find_label_exact(hero, "studio.novelforge.wei-dev.com")
	if host != null and host.get_parent() != null and host.get_parent().get_parent() is Control:
		var terminal := host.get_parent().get_parent() as Control
		var parent := terminal.get_parent()
		parent.remove_child(terminal)
		terminal.free()
		var terminal_y := 710.0 if _locale == "en-US" else 625.0
		_build_studio_terminal(hero, Vector2(40.0, terminal_y), Vector2(hero.size.x - 80.0, 227.0))
	var signature := _find_label_exact(hero, "✦ Studio ♡")
	if signature != null:
		signature.position = Vector2(hero.size.x - 140.0, target_height - 52.0)
	_shift_stage_controls(900.0, delta, hero)
	_stage.custom_minimum_size.y += delta

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

func _patch_publication_compact() -> void:
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var narrow := size.x < 900.0
	var target_height := (1210.0 if _locale == "en-US" else 1120.0) if narrow else (860.0 if _locale == "en-US" else 770.0)
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
			_build_format_showcase(hero, Vector2(44.0, showcase_y), Vector2(hero.size.x - 88.0, 620.0 if narrow else 280.0), narrow)
	_shift_stage_controls(700.0, delta, hero)
	_stage.custom_minimum_size.y += delta

func _patch_inspect_compact() -> void:
	var hero := _find_stage_panel(110.0, 400.0)
	if hero == null:
		return
	var target_height := 730.0 if _locale == "en-US" else 665.0
	var delta := target_height - hero.size.y
	_resize_hero(hero, target_height, 8.0)
	var file_name := _find_label_exact(hero, "novelforge.toml")
	if file_name != null and file_name.get_parent() != null and file_name.get_parent().get_parent() is Control:
		var stack := file_name.get_parent().get_parent() as Control
		var parent := stack.get_parent()
		parent.remove_child(stack)
		stack.free()
		var stack_y := 410.0 if _locale == "en-US" else 345.0
		_build_manifest_stack(hero, Vector2(48.0, stack_y), Vector2(hero.size.x - 96.0, 250.0), true)
	_shift_stage_controls(580.0, delta, hero)
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

func _patch_architecture_desktop() -> void:
	var hero := _find_stage_panel(122.0, 430.0)
	if hero == null:
		return
	_resize_hero(hero, 402.0, 8.0)
	var title := _find_label_prefix(hero, "See how one\nNovelForge run")
	if title != null:
		title.text = "See how one NovelForge run\nmoves through the system."
		title.position.y = 96.0
		title.size = Vector2(690.0, 132.0)
		title.add_theme_font_override("font", _heading_font(-5))
	var lede := _find_label_prefix(hero, "Project → Manager")
	if lede != null:
		lede.position.y = 242.0
	var docs := _find_button_exact(hero, "Read architecture docs")
	if docs != null:
		docs.position.y = 315.0
	var play := _find_button_exact(hero, "▷ Playground")
	if play != null:
		play.position.y = 315.0
	var project_label := _find_label_exact(hero, "Project")
	if project_label != null and project_label.get_parent() != null and project_label.get_parent().get_parent() is Control:
		var grid := project_label.get_parent().get_parent() as Control
		grid.position = Vector2(774.0, 43.0)
		grid.size = Vector2(468.0, 316.0)
		_resize_architecture_grid(grid)
	_shift_stage_controls(600.0, -59.0, hero)
	_stage.custom_minimum_size.y = max(_stage.custom_minimum_size.y - 59.0, 1120.0)

func _patch_architecture_phone() -> void:
	var hero := _find_stage_panel(89.0, 1000.0)
	if hero == null:
		return
	var title := _find_label_prefix(hero, "See how one\nNovelForge run")
	if title != null:
		title.position.y = 81.0
	var lede := _find_label_prefix(hero, "Project → Manager")
	if lede != null:
		lede.position.y = 261.0
	var docs := _find_button_exact(hero, "Read architecture docs")
	if docs != null:
		docs.position.y = 371.0
	var play := _find_button_exact(hero, "▷ Playground")
	if play != null:
		play.position.y = 426.0

func _patch_inspect_phone() -> void:
	var hero := _find_stage_panel(89.0, 600.0)
	if hero == null:
		return
	_resize_hero(hero, 592.0, 6.0)
	var title := _find_label_prefix(hero, "Resolve the\nproject before")
	if title != null:
		title.text = "Resolve the\nproject before any\ntool touches it."
		title.position.y = 45.0
		title.size.y = 150.0
	var lede := _find_label_prefix(hero, "Inspect the manifest")
	if lede != null:
		lede.text = "Inspect the manifest, exact Framework lock,\nattestation, and structural evidence locally.\nFiles are not uploaded and inspection grants\nno new Project authority."
		lede.position.y = 184.0
	var file_name := _find_label_exact(hero, "novelforge.toml")
	if file_name != null and file_name.get_parent() != null and file_name.get_parent().get_parent() is Control:
		var stack := file_name.get_parent().get_parent() as Control
		stack.position.y = 297.0
		var local_only := _find_label_exact(stack, "LOCAL ONLY")
		if local_only != null and local_only.get_parent() is Control:
			(local_only.get_parent() as Control).position.y = 22.0
	_shift_stage_controls(730.0, -41.0, hero)
	_stage.custom_minimum_size.y = max(_stage.custom_minimum_size.y - 41.0, 1500.0)

func _patch_playground_phone() -> void:
	var hero := _find_stage_panel(89.0, 700.0)
	if hero == null:
		return
	var title := _find_label_prefix(hero, "Make the\nexecution path")
	if title != null:
		title.position.y = 45.0
	var lede := _find_label_prefix(hero, "Paste working text")
	if lede != null:
		lede.text = "Paste working text, choose a task mode, and\ninspect a browser-local trace. No model call\nand no Project-state write."
		lede.add_theme_font_override("font", _spaced_latin_font(420, -1))
	var draft := _find_label_exact(hero, "DRAFT")
	if draft != null and draft.get_parent() != null and draft.get_parent().get_parent() != null and draft.get_parent().get_parent().get_parent() is Control:
		var row := draft.get_parent() as Control
		var inner := row.get_parent() as Control
		var canvas := inner.get_parent() as Control
		canvas.position.x = 18.0
		canvas.size.x = hero.size.x - 36.0
		inner.size.x = canvas.size.x - 36.0
		for child in inner.get_children():
			if child is Control:
				var control := child as Control
				if control == row or control.position.x >= 17.0:
					if control is Panel:
						control.size.x = inner.size.x - 36.0
					elif control is Label and control.size.x > 100.0:
						control.size.x = inner.size.x
		var note := _find_label_prefix(canvas, "✦ deterministic preview")
		if note != null:
			note.position.x = canvas.size.x - 158.0

func _resize_architecture_grid(grid: Control) -> void:
	for child in grid.get_children():
		if child is ColorRect:
			var line := child as ColorRect
			if line.size.x <= 1.5:
				line.size.y = grid.size.y
			elif line.size.y <= 1.5:
				line.size.x = grid.size.x
			if line.position.x > grid.size.x or line.position.y > grid.size.y:
				line.visible = false
	var names := ["Project", "Manager", "Context", "Worker", "Gate", "Settlement", "Publication"]
	var cell_w := 55.0
	var gap := 8.0
	for i in range(names.size()):
		var label := _find_label_exact(grid, str(names[i]))
		if label == null or not (label.get_parent() is Control):
			continue
		var cell := label.get_parent() as Control
		cell.position = Vector2(36.0 + i * (cell_w + gap), 112.0)
		cell.size = Vector2(cell_w, 92.0)
		for nested in cell.get_children():
			if nested is Label:
				(nested as Label).size.x = cell_w

func _resize_hero(hero: Control, target_height: float, inset: float) -> void:
	# Capture the pre-resize frame height before changing the parent. Expansion
	# previously compared the inset border against the *new* height, so the frame
	# never grew and stacked compact evidence visually fell out of its card.
	var previous_height := hero.size.y
	var previous_inner_height := maxf(previous_height - inset * 2.0, 0.0)
	hero.size.y = target_height
	for child in hero.get_children():
		if child is Control:
			var control := child as Control
			if abs(control.position.x - inset) < 1.0 and abs(control.position.y - inset) < 1.0 and control.size.y >= previous_inner_height - 60.0:
				control.size.y = maxf(target_height - inset * 2.0, 0.0)
				break

func _shift_stage_controls(min_y: float, delta: float, except_control: Control) -> void:
	if _stage == null:
		return
	for child in _stage.get_children():
		if child is Control:
			var control := child as Control
			if control != except_control and control.position.y >= min_y:
				control.position.y += delta
