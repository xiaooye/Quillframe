extends "res://scripts/editorial_surfaces.gd"

# WeiUI's checked-in typography authority is Inter for Latin UI text.
# CJK stays on Noto Sans SC, and broad Unicode fallback remains scoped to
# decorative controls so fallback ascent/descent cannot perturb body metrics.
const INTER_FONT_PATH := "res://generated/Inter-opsz-wght.ttf"

var _latin_base_font: Font
var _latin_font_cache := {}
var _cjk_font_cache := {}
var _latin_mixed_font_cache := {}
var _heading_font_cache := {}

func _ready() -> void:
	_latin_base_font = load(INTER_FONT_PATH) as Font
	if _latin_base_font == null:
		push_error("NovelForge Godot parity shadow requires the pinned Inter font")
	super._ready()

func _build() -> void:
	super._build()
	_reset_label_scale(self)
	_calibrate_inter_heading_rhythm(self)

func _font(weight: int) -> Font:
	if _latin_font_cache.has(weight):
		return _latin_font_cache[weight]
	var variation := FontVariation.new()
	variation.base_font = _latin_base_font
	var text_server := TextServerManager.get_primary_interface()
	variation.variation_opentype = {text_server.name_to_tag("wght"): weight}
	_latin_font_cache[weight] = variation
	return variation

func _heading_font(glyph_spacing: int, optical_size: int) -> Font:
	var key := "%d:%d" % [glyph_spacing, optical_size]
	if _heading_font_cache.has(key):
		return _heading_font_cache[key]
	var variation := FontVariation.new()
	variation.base_font = _latin_base_font
	variation.spacing_glyph = glyph_spacing
	variation.spacing_space = glyph_spacing
	var text_server := TextServerManager.get_primary_interface()
	variation.variation_opentype = {
		text_server.name_to_tag("wght"): 780,
		text_server.name_to_tag("opsz"): optical_size,
	}
	_heading_font_cache[key] = variation
	return variation

func _cjk_font(weight: int) -> Font:
	if _cjk_font_cache.has(weight):
		return _cjk_font_cache[weight]
	var variation := FontVariation.new()
	variation.base_font = _base_font
	var text_server := TextServerManager.get_primary_interface()
	variation.variation_opentype = {text_server.name_to_tag("wght"): weight}
	_cjk_font_cache[weight] = variation
	return variation

func _mixed_font(weight: int) -> Font:
	if _latin_mixed_font_cache.has(weight):
		return _latin_mixed_font_cache[weight]
	var variation := FontVariation.new()
	variation.base_font = _latin_base_font
	var fallbacks: Array[Font] = []
	if _base_font != null:
		fallbacks.append(_base_font)
	fallbacks.append_array(_fallback_fonts)
	variation.fallbacks = fallbacks
	var text_server := TextServerManager.get_primary_interface()
	variation.variation_opentype = {text_server.name_to_tag("wght"): weight}
	_latin_mixed_font_cache[weight] = variation
	return variation

func _label(text: String, font_size: int, weight: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_override("font", _cjk_font(weight) if _contains_cjk(text) else _font(weight))
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	if text.begins_with("NovelForge connects") or text.begins_with("NovelForge 把创作"):
		if _layout == "phone":
			label.add_theme_constant_override("line_spacing", MOBILE_LEDE_LINE_SPACING)
		elif _layout == "desktop":
			label.add_theme_constant_override("line_spacing", DESKTOP_LEDE_LINE_SPACING)
	return label

func _mixed_label(text: String, font_size: int, weight: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_override("font", _mixed_font(weight))
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label

func _make_text_button(text: String, pos: Vector2, button_size: Vector2, bg: Color, fg: Color, font_size: int, weight: int, radius: int, mixed: bool) -> Button:
	var button := Button.new()
	button.text = text
	button.position = pos
	button.size = button_size
	button.focus_mode = Control.FOCUS_ALL
	var font := _mixed_font(weight) if mixed else (_cjk_font(weight) if _contains_cjk(text) else _font(weight))
	button.add_theme_font_override("font", font)
	button.add_theme_font_size_override("font_size", font_size)
	button.add_theme_color_override("font_color", fg)
	button.add_theme_color_override("font_hover_color", fg)
	button.add_theme_color_override("font_pressed_color", fg)
	button.add_theme_stylebox_override("normal", _button_box(bg, radius))
	button.add_theme_stylebox_override("hover", _button_box(bg.lightened(0.025) if bg.a > 0.0 else Color(0.48,0.42,0.77,0.08), radius))
	button.add_theme_stylebox_override("pressed", _button_box(bg.darkened(0.04) if bg.a > 0.0 else Color(0.48,0.42,0.77,0.12), radius))
	button.add_theme_stylebox_override("focus", _focus_box(radius))
	return button

func _contains_cjk(text: String) -> bool:
	for i in range(text.length()):
		var code := text.unicode_at(i)
		if (code >= 0x3400 and code <= 0x4DBF) or (code >= 0x4E00 and code <= 0x9FFF) or (code >= 0xF900 and code <= 0xFAFF):
			return true
	return false

func _reset_label_scale(node: Node) -> void:
	for child in node.get_children():
		if child is Label:
			(child as Label).scale = Vector2.ONE
		_reset_label_scale(child)

func _calibrate_inter_heading_rhythm(node: Node) -> void:
	for child in node.get_children():
		if child is Label:
			var label := child as Label
			if _is_english_heading(label.text):
				var route := _current_route()
				var delta := 10
				if route == "/" and _layout == "desktop" and label.text.begins_with("Let the story"):
					delta = 15
				var current := label.get_theme_constant("line_spacing")
				label.add_theme_constant_override("line_spacing", current + delta)
				# ProductSurface CSS uses letter-spacing:-.052em and browsers
				# resolve Inter's optical-size axis from the rendered h1 size.
				# Mirror both instead of compensating with layout width or font size.
				if route != "/":
					var optical_size := 39 if _layout == "phone" else 62
					label.add_theme_font_override("font", _heading_font(-2 if _layout == "phone" else -3, optical_size))
		_calibrate_inter_heading_rhythm(child)

func _is_english_heading(text: String) -> bool:
	return text.begins_with("Let the story") \
		or text.begins_with("NovelForge is a") \
		or text.begins_with("The creative") \
		or text.begins_with("A changelog") \
		or text.begins_with("Resolve the") \
		or text.begins_with("Make the") \
		or text.begins_with("Let your") \
		or text.begins_with("See how one") \
		or text.begins_with("One accepted") \
		or text.begins_with("many\n")