extends "res://scripts/mobile_geometry_parity.gd"

# Final cross-viewport geometry bridge. Solid/Vite remains the screenshot
# authority; this layer only reproduces browser CSS flow where fixed Godot
# controls would otherwise change wrapping, hero height, or column geometry.

var _home_heading_fonts := {}

func _build() -> void:
	super._build()
	_patch_shared_symbol_fonts()
	_patch_home_typography()
	if _layout != "desktop":
		return
	match _current_route():
		"/product":
			_patch_product_desktop()
		"/studio":
			_patch_studio_desktop()
		"/architecture":
			_patch_architecture_desktop()

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

func _patch_home_typography() -> void:
	if _current_route() != "/" or _locale != "en-US":
		return
	var title := _find_label_prefix(self, "Let the story\ngrow without")
	if title != null:
		title.add_theme_font_override("font", _home_heading_font(-4 if _layout == "desktop" else -3))
		if _layout == "desktop":
			title.position.y = 202.0
	var lede := _find_label_prefix(self, "NovelForge connects creation")
	if lede != null and _layout == "phone":
		lede.add_theme_constant_override("line_spacing", 7)

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

	var lede := _find_label_prefix(hero, "It separates creative judgment")
	if lede != null:
		lede.text = "It separates creative judgment from deterministic control so a long-running\nbook can accumulate evidence, revisions, and state without turning every\nprevious model output into truth."
		lede.position.y = 282.0
		lede.size = Vector2(650.0, 102.0)

	var story_state := _find_label_exact(hero, "♡ STORY STATE")
	if story_state != null and story_state.get_parent() != null and story_state.get_parent().get_parent() is Control:
		var stack := story_state.get_parent().get_parent() as Control
		stack.size.y = 300.0
		var names := ["Canon", "Context", "Evidence", "Candidate", "Settlement"]
		for i in range(names.size()):
			var row_label := _find_label_exact(stack, str(names[i]))
			if row_label != null and row_label.get_parent() is Control:
				var row := row_label.get_parent() as Control
				row.position.y = 33.0 + i * 54.0

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
	hero.size.y = target_height
	for child in hero.get_children():
		if child is Control:
			var control := child as Control
			if abs(control.position.x - inset) < 1.0 and abs(control.position.y - inset) < 1.0 and control.size.y > target_height - 60.0:
				control.size.y = target_height - inset * 2.0
				break

func _shift_stage_controls(min_y: float, delta: float, except_control: Control) -> void:
	if _stage == null:
		return
	for child in _stage.get_children():
		if child is Control:
			var control := child as Control
			if control != except_control and control.position.y >= min_y:
				control.position.y += delta
