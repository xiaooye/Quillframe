extends "res://scripts/main.gd"

const LAUNCHER_CONTENT_INSET := 36.0
const LAUNCHER_CONTENT_GAP := 12.0
const MOBILE_LEDE_LINE_SPACING := 3
const DESKTOP_LEDE_LINE_SPACING := 4

func _build() -> void:
	super._build()
	_style_scrollbar()

func _label(text: String, font_size: int, weight: int, color: Color) -> Label:
	var label := super._label(text, font_size, weight, color)
	if text.begins_with("NovelForge connects") or text.begins_with("NovelForge 把创作"):
		if _layout == "phone":
			label.add_theme_constant_override("line_spacing", MOBILE_LEDE_LINE_SPACING)
		elif _layout == "desktop":
			label.add_theme_constant_override("line_spacing", DESKTOP_LEDE_LINE_SPACING)
	return label

func _build_header() -> void:
	super._build_header()
	if _layout != "phone" or get_child_count() == 0:
		return
	var header := get_child(get_child_count() - 1)
	if not header is Panel:
		return
	for child in header.get_children():
		if child is Button:
			var button := child as Button
			if button.text == "中文" or button.text == "EN":
				button.position.x -= 10.0
				button.add_theme_font_size_override("font_size", 13)
			elif button.text == "◐":
				button.position.x -= 8.0
			elif button.text == "≡":
				button.position.x -= 4.0

func _style_scrollbar() -> void:
	if _scroll == null:
		return
	var bar := _scroll.get_v_scroll_bar()
	if bar == null:
		return
	var track := StyleBoxEmpty.new()
	bar.add_theme_stylebox_override("scroll", track)
	bar.add_theme_stylebox_override("scroll_focus", track)
	var grabber := StyleBoxFlat.new()
	grabber.bg_color = Color("b0a8da")
	grabber.corner_radius_top_left = 4
	grabber.corner_radius_top_right = 4
	grabber.corner_radius_bottom_left = 4
	grabber.corner_radius_bottom_right = 4
	bar.add_theme_stylebox_override("grabber", grabber)
	bar.add_theme_stylebox_override("grabber_highlight", grabber)
	bar.add_theme_stylebox_override("grabber_pressed", grabber)

func _build_launcher(pos: Vector2, launcher_size: Vector2) -> void:
	var card := _panel(pos, launcher_size, Color("f4f8fb"), 22, Color("cbd7e7"), 1, Color(0.18, 0.12, 0.24, 0.10), 16)
	_stage.add_child(card)
	var back := _panel(Vector2(-22, 15), Vector2(launcher_size.x - 24, launcher_size.y - 28), Color(1,1,1,0.38), 18, Color("d8cae8"), 1, Color(0.18,0.12,0.24,0.06), 8)
	back.rotation_degrees = -1.4
	card.add_child(back)
	card.move_child(back, 0)

	var inset := LAUNCHER_CONTENT_INSET
	var content_width := launcher_size.x - inset * 2.0

	var hint := _panel(Vector2(inset, 32), Vector2(250, 56), C.editorial_soft, 14, Color("efc6d8"), 1)
	var hint_text := _mixed_label("Let’s weave something lovely today (｡•̀ᴗ-)✧" if _locale == "en-US" else "今天也把故事织得更漂亮一点吧 (｡•̀ᴗ-)✧", 12, 480, C.editorial)
	hint_text.position = Vector2(13, 9)
	hint_text.size = Vector2(220, 40)
	hint_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.add_child(hint_text)
	card.add_child(hint)

	var tab := _panel(Vector2(launcher_size.x - 168, -16), Vector2(122, 38), Color("fff2da"), 5, Color("efd8af"), 1, Color(0.2,0.12,0.14,0.08), 8)
	tab.rotation_degrees = 3.0
	var tab_text := _label("♡ Story Loom", 11, 720, C.editorial)
	tab_text.position = Vector2(16, 10)
	tab_text.size = Vector2(95, 20)
	tab.add_child(tab_text)
	card.add_child(tab)

	var search := _panel(Vector2(inset, 99), Vector2(content_width, 49), Color("fffdf9"), 13, Color("ead4c4"), 1)
	var search_label := _label("⌕  Search product, docs, architecture, publication…" if _locale == "en-US" else "⌕  搜索产品、文档、架构、出版…", 14, 430, C.muted)
	search_label.position = Vector2(13, 13)
	search_label.size = Vector2(max(content_width - 165.0, 120.0), 25)
	search.add_child(search_label)
	var shortcut := _label("⌘K / Ctrl+K", 12, 560, C.muted)
	shortcut.position = Vector2(content_width - 132.0, 14)
	shortcut.size = Vector2(120, 22)
	search.add_child(shortcut)
	card.add_child(search)

	var gap := LAUNCHER_CONTENT_GAP
	var tile_w := (content_width - gap) / 2.0
	var tile_h := 82.0
	var tile_y := 162.0
	card.add_child(_launcher_tile(Vector2(inset, tile_y), Vector2(tile_w, tile_h), "✦", "Studio", "Start operating" if _locale == "en-US" else "真正开始操作", C.runtime_soft, Color("cfc3ee"), true))
	card.add_child(_launcher_tile(Vector2(inset + tile_w + gap, tile_y), Vector2(tile_w, tile_h), "♡", "Product" if _locale == "en-US" else "产品能力", "See what it solves" if _locale == "en-US" else "看它解决什么", C.editorial_soft, Color("f0cedd"), false))
	card.add_child(_launcher_tile(Vector2(inset, tile_y + tile_h + gap), Vector2(tile_w, tile_h), "📚", "Knowledge" if _locale == "en-US" else "知识库", "Search real docs" if _locale == "en-US" else "搜索真实文档", C.evidence_soft, Color("eddcbb"), false))
	card.add_child(_launcher_tile(Vector2(inset + tile_w + gap, tile_y + tile_h + gap), Vector2(tile_w, tile_h), "✧", "Publication" if _locale == "en-US" else "出版", "Accepted text to formats" if _locale == "en-US" else "从接受稿到派生格式", C.valid_soft, Color("cde7dd"), false))

	var footer := _label("0.8.x                                      pre-1.0 · actively evolving                                      authority=false" if _locale == "en-US" else "0.8.x                                      pre-1.0 · 快速演进                                      authority=false", 10, 480, Color("857c8b"))
	footer.position = Vector2(inset, launcher_size.y - 51)
	footer.size = Vector2(content_width, 24)
	card.add_child(footer)
