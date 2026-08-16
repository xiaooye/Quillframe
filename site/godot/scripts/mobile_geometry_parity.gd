extends "res://scripts/typography_parity.gd"

# Final mobile geometry corrections are intentionally isolated from the route
# implementations. The Solid/Vite Kawaii Atelier screenshots remain the visual
# authority; this layer only compensates for Godot text-flow differences.

const PRODUCT_PHONE_HERO_HEIGHT := 690.0
const PRODUCT_PHONE_FLOW_SHIFT := 96.0

func _build() -> void:
	super._build()
	if _layout != "phone":
		return
	match _current_route():
		"/product":
			_patch_product_phone()
		"/studio":
			_patch_studio_phone()
		"/publication":
			_patch_publication_phone()

func _patch_product_phone() -> void:
	var title := _find_label_prefix(self, "NovelForge\nis a fiction")
	if title != null:
		title.text = "NovelForge is a\nfiction production\nsystem, not a\nprompt wrapper."
		title.position.y = 46.0
		title.size.y = 190.0
		title.add_theme_constant_override("line_spacing", -2)
		title.add_theme_font_override("font", _heading_font(-2))

	var lede := _find_label_prefix(self, "It separates creative judgment")
	if lede != null:
		lede.position.y = 228.0

	var story_state := _find_label_exact(self, "♡ STORY STATE")
	if story_state != null and story_state.get_parent() != null and story_state.get_parent().get_parent() is Control:
		var stack := story_state.get_parent().get_parent() as Control
		stack.position.y = 374.0

	if _stage != null:
		for child in _stage.get_children():
			if child is Control:
				var control := child as Control
				if abs(control.position.y - 89.0) < 1.0 and control.size.y > 740.0:
					control.size.y = PRODUCT_PHONE_HERO_HEIGHT
				elif control.position.y >= 895.0:
					control.position.y -= PRODUCT_PHONE_FLOW_SHIFT
		_stage.custom_minimum_size.y = max(_stage.custom_minimum_size.y - PRODUCT_PHONE_FLOW_SHIFT, 1500.0)

func _patch_studio_phone() -> void:
	var title := _find_label_prefix(self, "The creative\nworkbench\naround Core —\nwith\n")
	if title != null:
		title.text = "The creative\nworkbench\naround Core —\nwith progressive\ndisclosure instead\nof dashboard\noverload."
		title.size.y = 315.0

	var lede := _find_label_prefix(self, "Phase 2C now ships")
	if lede != null:
		lede.position.y = 350.0

	var cta := _find_button_exact(self, "✦ Open Hosted Studio")
	if cta != null:
		cta.position.y = 488.0

	var host := _find_label_exact(self, "studio.novelforge.wei-dev.com")
	if host != null and host.get_parent() != null and host.get_parent().get_parent() is Control:
		var terminal := host.get_parent().get_parent() as Control
		terminal.position.y = 573.0

func _patch_publication_phone() -> void:
	var pink := _find_label_prefix(self, "many\ndeterministic\nderivatives.")
	if pink != null and pink.get_parent() is Control:
		var hero := pink.get_parent() as Control
		pink.text = "many"
		pink.position = Vector2(218.0, 124.0)
		pink.size = Vector2(125.0, 56.0)
		pink.add_theme_constant_override("line_spacing", -8)
		pink.add_theme_font_override("font", _heading_font(-2))

		var continuation := _label("deterministic\nderivatives.", 39, 780, Color("e94c9a"))
		continuation.position = Vector2(18.0, 166.0)
		continuation.size = Vector2(max(hero.size.x - 36.0, 200.0), 108.0)
		continuation.add_theme_constant_override("line_spacing", -8)
		continuation.add_theme_font_override("font", _heading_font(-2))
		hero.add_child(continuation)

	var lede := _find_label_prefix(self, "One Publication IR produces")
	if lede != null:
		lede.position.y = 263.0

	var publication_hero := _find_stage_panel(89.0, 1000.0)
	if publication_hero != null:
		var showcase := _find_large_child_panel(publication_hero, 300.0, 600.0)
		if showcase != null:
			showcase.position.y = 388.0
			_fix_epub_card_position(showcase)

func _fix_epub_card_position(showcase: Control) -> void:
	var epub_tag := _find_negative_y_label(showcase, "EPUB")
	if epub_tag == null or epub_tag.get_parent() == null or not (epub_tag.get_parent().get_parent() is Control):
		return
	var card := epub_tag.get_parent().get_parent() as Control
	var gap := 12.0
	var card_w := (showcase.size.x - gap - 20.0) / 2.0
	card.position = Vector2(10.0 + card_w + gap, 312.0)

func _find_stage_panel(y: float, min_height: float) -> Control:
	if _stage == null:
		return null
	for child in _stage.get_children():
		if child is Control:
			var control := child as Control
			if abs(control.position.y - y) < 1.0 and control.size.y >= min_height:
				return control
	return null

func _find_large_child_panel(parent: Node, min_y: float, min_height: float) -> Control:
	for child in parent.get_children():
		if child is Control:
			var control := child as Control
			if control.position.y >= min_y and control.size.y >= min_height:
				return control
	return null

func _find_label_prefix(node: Node, prefix: String) -> Label:
	for child in node.get_children():
		if child is Label and (child as Label).text.begins_with(prefix):
			return child as Label
		var nested := _find_label_prefix(child, prefix)
		if nested != null:
			return nested
	return null

func _find_label_exact(node: Node, text: String) -> Label:
	for child in node.get_children():
		if child is Label and (child as Label).text == text:
			return child as Label
		var nested := _find_label_exact(child, text)
		if nested != null:
			return nested
	return null

func _find_negative_y_label(node: Node, text: String) -> Label:
	for child in node.get_children():
		if child is Label and (child as Label).text == text and child.get_parent() is Control:
			var parent := child.get_parent() as Control
			if parent.position.y < 0.0:
				return child as Label
		var nested := _find_negative_y_label(child, text)
		if nested != null:
			return nested
	return null

func _find_button_exact(node: Node, text: String) -> Button:
	for child in node.get_children():
		if child is Button and (child as Button).text == text:
			return child as Button
		var nested := _find_button_exact(child, text)
		if nested != null:
			return nested
	return null
