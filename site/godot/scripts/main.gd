extends Control

const FONT_PATH := "res://generated/NotoSansSC-wght.ttf"
const SYMBOL_FONT_PATH := "res://generated/NotoSansSymbols2-Regular.ttf"
const THAI_FONT_PATH := "res://generated/NotoSansThai-wdth-wght.ttf"
const ARABIC_FONT_PATH := "res://generated/NotoSansArabic-wdth-wght.ttf"
const MARK_PATH := "res://assets/novelforge-mark.svg"
const BOOKS_ICON_PATH := "res://assets/books-stack.svg"
const STUDIO_URL := "https://studio.novelforge.wei-dev.com"

const C := {
	"bg": Color("fffdfc"),
	"surface": Color("fffdfc"),
	"surface_soft": Color("f8f4fa"),
	"ink": Color("261f2d"),
	"muted": Color("665c70"),
	"line": Color("e8ddea"),
	"project": Color("75badd"),
	"project_soft": Color("eaf7fc"),
	"runtime": Color("796bc4"),
	"runtime_soft": Color("f2eefb"),
	"editorial": Color("d6679a"),
	"editorial_soft": Color("fff0f6"),
	"evidence": Color("c79539"),
	"evidence_soft": Color("fff8e9"),
	"valid": Color("5cae92"),
	"valid_soft": Color("eef9f5"),
}

var _base_font: Font
var _fallback_fonts: Array[Font] = []
var _font_cache := {}
var _locale := "en-US"
var _layout := "desktop"
var _scroll: ScrollContainer
var _stage: Control
var _mark: Texture2D
var _books_icon: Texture2D

func _ready() -> void:
	_base_font = load(FONT_PATH) as Font
	_mark = load(MARK_PATH) as Texture2D
	_books_icon = load(BOOKS_ICON_PATH) as Texture2D
	if _base_font == null:
		push_error("NovelForge Godot parity shadow requires the pinned Noto Sans SC font")
	for fallback_path in [SYMBOL_FONT_PATH, THAI_FONT_PATH, ARABIC_FONT_PATH]:
		var fallback := load(fallback_path) as Font
		if fallback == null:
			push_error("NovelForge Godot parity shadow missing fallback font: %s" % fallback_path)
		else:
			_fallback_fonts.append(fallback)
	if _mark == null or _books_icon == null:
		push_error("NovelForge Godot parity shadow requires local vector UI assets")
	get_viewport().size_changed.connect(_on_viewport_changed)
	_locale = _initial_locale()
	_build()
	_publish_ready()

func _on_viewport_changed() -> void:
	var next_layout := _layout_for_width(size.x)
	if next_layout != _layout:
		_build()
	else:
		queue_redraw()

func _layout_for_width(width: float) -> String:
	if width < 720.0:
		return "phone"
	if width < 1120.0:
		return "compact"
	return "desktop"

func _initial_locale() -> String:
	if OS.has_feature("web"):
		var value = JavaScriptBridge.eval("(() => { const q=new URLSearchParams(location.search).get('locale'); return q || localStorage.getItem('novelforge.locale') || navigator.language || 'en-US'; })()")
		if typeof(value) == TYPE_STRING and str(value).to_lower().begins_with("zh"):
			return "zh-CN"
	return "en-US"

func _font(weight: int) -> Font:
	if _font_cache.has(weight):
		return _font_cache[weight]
	var variation := FontVariation.new()
	variation.base_font = _base_font
	variation.fallbacks = _fallback_fonts
	var text_server := TextServerManager.get_primary_interface()
	variation.variation_opentype = {text_server.name_to_tag("wght"): weight}
	_font_cache[weight] = variation
	return variation

func _clear() -> void:
	for child in get_children():
		remove_child(child)
		child.free()

func _build() -> void:
	_clear()
	_layout = _layout_for_width(size.x)
	queue_redraw()
	_scroll = ScrollContainer.new()
	_scroll.name = "ParityScroll"
	_scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	_scroll.follow_focus = true
	add_child(_scroll)

	_stage = Control.new()
	_stage.name = "ParityStage"
	var stage_height := 1760.0 if _layout == "desktop" else (1580.0 if _layout == "compact" else 1750.0)
	_stage.custom_minimum_size = Vector2(max(size.x, 320.0), stage_height)
	_scroll.add_child(_stage)

	if _layout == "desktop":
		_build_desktop()
	elif _layout == "compact":
		_build_compact()
	else:
		_build_phone()
	_build_header()

func _build_header() -> void:
	var width := size.x
	var margin := 32.0 if _layout == "desktop" else (18.0 if _layout == "compact" else 7.0)
	var header := _panel(Vector2(margin, 10), Vector2(width - margin * 2.0, 54), C.surface, 14, Color("cfc0e7"), 1, Color(0.18, 0.12, 0.24, 0.08), 9)
	header.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(header)

	var mark_box := TextureRect.new()
	mark_box.texture = _mark
	mark_box.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	mark_box.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	mark_box.position = Vector2(10, 7)
	mark_box.size = Vector2(40, 40)
	header.add_child(mark_box)

	if _layout != "phone":
		var brand := _label("NovelForge", 20, 760, C.ink)
		brand.position = Vector2(56, 14)
		brand.size = Vector2(132, 28)
		header.add_child(brand)
		var version := _pill("0.8.x", Vector2(174, 16), Vector2(48, 22), C.runtime_soft, C.runtime, 10, 650)
		header.add_child(version)
		var nav_x := 250.0
		for item in [["Product", "/product"], ["Studio", "/studio"], ["Architecture", "/architecture"], ["Publication", "/publication"], ["Docs", "/docs"]]:
			var nav_width := 112.0 if item[0] == "Architecture" else 82.0
			var nav := _text_button(str(item[0]), Vector2(nav_x, 8), Vector2(nav_width, 38), Color(0,0,0,0), C.muted, 13, 650, 10)
			nav.pressed.connect(_navigate.bind(str(item[1])))
			header.add_child(nav)
			nav_x += nav.size.x + 2.0
		if width >= 1280.0:
			var header_width := width - margin * 2.0
			var search := _panel(Vector2(header_width - 514, 8), Vector2(266, 38), Color("fffaf7"), 12, Color("ead6c7"), 1)
			var search_text := _label("⌕  Search NovelForge", 13, 430, C.muted)
			search_text.position = Vector2(14, 9)
			search_text.size = Vector2(170, 22)
			search.add_child(search_text)
			var key := _pill("⌘K / Ctrl+K", Vector2(174, 7), Vector2(82, 24), C.surface_soft, C.muted, 10, 600)
			search.add_child(key)
			header.add_child(search)
			var studio := _text_button("✦ Open Studio", Vector2(header_width - 238, 4), Vector2(126, 46), C.runtime, Color.WHITE, 13, 650, 14)
			studio.pressed.connect(_open_external.bind(STUDIO_URL))
			header.add_child(studio)
			var lang := _text_button("中文" if _locale == "en-US" else "EN", Vector2(header_width - 108, 8), Vector2(58, 38), Color(0,0,0,0), C.runtime, 13, 620, 10)
			lang.pressed.connect(_toggle_locale)
			header.add_child(lang)
			var theme := _text_button("◐", Vector2(header_width - 48, 8), Vector2(38, 38), Color(0,0,0,0), C.runtime, 16, 650, 10)
			header.add_child(theme)
	else:
		var header_width_phone := width - margin * 2.0
		var lang_phone := _text_button("中文" if _locale == "en-US" else "EN", Vector2(header_width_phone - 158, 8), Vector2(66, 38), Color(0,0,0,0), C.runtime, 15, 620, 10)
		lang_phone.pressed.connect(_toggle_locale)
		header.add_child(lang_phone)
		var theme_phone := _text_button("◐", Vector2(header_width_phone - 91, 8), Vector2(38, 38), Color(0,0,0,0), C.runtime, 16, 650, 10)
		header.add_child(theme_phone)
		var menu_phone := _text_button("≡", Vector2(header_width_phone - 47, 8), Vector2(38, 38), Color(0,0,0,0), C.runtime, 17, 700, 10)
		header.add_child(menu_phone)

func _build_desktop() -> void:
	var left_x := 70.0
	var top := 166.0
	var badge_text := "Long-form fiction system · 0.8.x" if _locale == "en-US" else "长篇小说创作系统 · 0.8.x"
	_stage.add_child(_pill(badge_text, Vector2(left_x, top), Vector2(208 if _locale == "en-US" else 194, 25), Color("f8fbff"), Color("4078a8"), 12, 500, Color("b8d8ee")))
	_stage.add_child(_pill("ฅ^•ﻌ•^ฅ", Vector2(left_x + 219, top), Vector2(82, 25), C.editorial_soft, C.editorial, 12, 550, Color("f0c9da")))

	var title_text := "Let the story\ngrow without\nletting the\nsystem lose\nthe plot." if _locale == "en-US" else "让故事越写越长，\n系统仍然知道\n自己在做什么。"
	var title := _label(title_text, 72 if _locale == "en-US" else 61, 800, C.ink)
	title.position = Vector2(left_x, top + 24)
	title.size = Vector2(520, 356)
	title.scale = Vector2(1.045 if _locale == "en-US" else 1.0, 1.0)
	title.add_theme_constant_override("line_spacing", -33 if _locale == "en-US" else -15)
	_stage.add_child(title)

	var lede_text := "NovelForge connects creation, context, character knowledge,\nquality gates, and publication into one inspectable workflow.\nLaunch Studio, search real docs, explore architecture, or play\nwith the core boundaries from here." if _locale == "en-US" else "NovelForge 把创作、上下文、角色知识、质量审查与出版\n连成一套可检查的工作流。你可以从这里直接进入 Studio、\n搜索真实文档、探索架构，或者试试关键机制。"
	var lede := _label(lede_text, 17, 420, C.muted)
	lede.position = Vector2(left_x, top + 420)
	lede.size = Vector2(555, 112)
	lede.add_theme_constant_override("line_spacing", 7)
	_stage.add_child(lede)

	var studio := _text_button("✦ Open Studio" if _locale == "en-US" else "✦ 打开 Studio", Vector2(left_x, top + 552), Vector2(200, 56), C.runtime, Color.WHITE, 18, 600, 13)
	studio.pressed.connect(_open_external.bind(STUDIO_URL))
	_stage.add_child(studio)
	var knowledge := _text_button("Knowledge" if _locale == "en-US" else "知识库", Vector2(left_x + 210, top + 552), Vector2(194, 56), C.surface_soft, C.runtime, 18, 560, 13)
	knowledge.icon = _books_icon
	knowledge.pressed.connect(_navigate.bind("/docs"))
	_stage.add_child(knowledge)
	var architecture := _text_button("⌘ Architecture" if _locale == "en-US" else "⌘ 架构探索", Vector2(left_x + 14, top + 625), Vector2(190, 42), Color(0,0,0,0), C.runtime, 18, 520, 10)
	architecture.pressed.connect(_navigate.bind("/architecture"))
	_stage.add_child(architecture)
	_stage.add_child(_trust_pill(Vector2(left_x, top + 690), Vector2(398, 37)))

	_build_launcher(Vector2(650, 320), Vector2(max(size.x - 720.0, 620.0), 424))
	_build_lower_sections(930.0, 70.0, size.x - 140.0, false)

func _build_compact() -> void:
	var x := 40.0
	var top := 150.0
	_stage.add_child(_pill("Long-form fiction system · 0.8.x" if _locale == "en-US" else "长篇小说创作系统 · 0.8.x", Vector2(x, top), Vector2(208, 25), Color("f8fbff"), Color("4078a8"), 12, 500, Color("b8d8ee")))
	var title := _label("Let the story grow\nwithout letting the\nsystem lose the plot." if _locale == "en-US" else "让故事越写越长，\n系统仍然知道自己\n在做什么。", 58 if _locale == "en-US" else 50, 800, C.ink)
	title.position = Vector2(x, top + 32)
	title.size = Vector2(size.x - 80, 230)
	title.scale = Vector2(1.04 if _locale == "en-US" else 1.0, 1.0)
	title.add_theme_constant_override("line_spacing", -20 if _locale == "en-US" else -12)
	_stage.add_child(title)
	var lede := _label("NovelForge connects creation, context, character knowledge, quality gates, and publication into one inspectable workflow." if _locale == "en-US" else "NovelForge 把创作、上下文、角色知识、质量审查与出版连成一套可检查的工作流。", 17, 420, C.muted)
	lede.position = Vector2(x, top + 300)
	lede.size = Vector2(size.x - 80, 92)
	lede.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_stage.add_child(lede)
	var studio := _text_button("✦ Open Studio" if _locale == "en-US" else "✦ 打开 Studio", Vector2(x, top + 414), Vector2(210, 56), C.runtime, Color.WHITE, 18, 600, 13)
	studio.pressed.connect(_open_external.bind(STUDIO_URL))
	_stage.add_child(studio)
	var knowledge := _text_button("Knowledge" if _locale == "en-US" else "知识库", Vector2(x + 222, top + 414), Vector2(190, 56), C.surface_soft, C.runtime, 18, 560, 13)
	knowledge.icon = _books_icon
	knowledge.pressed.connect(_navigate.bind("/docs"))
	_stage.add_child(knowledge)
	_stage.add_child(_trust_pill(Vector2(x, top + 486), Vector2(398, 37)))
	_build_launcher(Vector2(x, top + 560), Vector2(size.x - 80, 390))
	_build_lower_sections(top + 1000, x, size.x - 80, false)

func _build_phone() -> void:
	var x := 16.0
	var top := 101.0
	_stage.add_child(_pill("Long-form fiction system · 0.8.x" if _locale == "en-US" else "长篇小说创作系统 · 0.8.x", Vector2(x, top), Vector2(212 if _locale == "en-US" else 200, 25), Color("f8fbff"), Color("4078a8"), 12, 500, Color("b8d8ee")))
	_stage.add_child(_pill("ฅ^•ﻌ•^ฅ", Vector2(x + 220, top), Vector2(88, 25), C.editorial_soft, C.editorial, 12, 550, Color("f0c9da")))

	var title_text := "Let the story\ngrow without\nletting the\nsystem lose\nthe plot." if _locale == "en-US" else "让故事越写越长，\n系统仍然知道\n自己在做什么。"
	var title := _label(title_text, 46 if _locale == "en-US" else 42, 800, C.ink)
	title.position = Vector2(x, top + 27)
	title.size = Vector2(size.x - 32, 262)
	title.scale = Vector2(1.055 if _locale == "en-US" else 1.0, 1.0)
	title.add_theme_constant_override("line_spacing", -20 if _locale == "en-US" else -13)
	_stage.add_child(title)

	var lede_text := "NovelForge connects creation, context,\ncharacter knowledge, quality gates, and\npublication into one inspectable workflow.\nLaunch Studio, search real docs, explore\narchitecture, or play with the core\nboundaries from here." if _locale == "en-US" else "NovelForge 把创作、上下文、角色知识、\n质量审查与出版连成一套可检查的工作流。\n你可以从这里直接进入 Studio、搜索真实\n文档、探索架构，或者试试关键机制。"
	var lede := _label(lede_text, 16, 420, C.muted)
	lede.position = Vector2(x, top + 300)
	lede.size = Vector2(size.x - 32, 166)
	lede.add_theme_constant_override("line_spacing", 8)
	_stage.add_child(lede)

	var studio := _text_button("✦ Open Studio" if _locale == "en-US" else "✦ 打开 Studio", Vector2(x, top + 482), Vector2(size.x - 32, 56), C.runtime, Color.WHITE, 18, 600, 13)
	studio.pressed.connect(_open_external.bind(STUDIO_URL))
	_stage.add_child(studio)
	var knowledge := _text_button("Knowledge" if _locale == "en-US" else "知识库", Vector2(x, top + 548), Vector2(size.x - 32, 56), C.surface_soft, C.runtime, 18, 560, 13)
	knowledge.icon = _books_icon
	knowledge.pressed.connect(_navigate.bind("/docs"))
	_stage.add_child(knowledge)
	var architecture := _text_button("⌘ Architecture" if _locale == "en-US" else "⌘ 架构探索", Vector2(x + 82, top + 622), Vector2(size.x - 196, 42), Color(0,0,0,0), C.runtime, 18, 520, 10)
	architecture.pressed.connect(_navigate.bind("/architecture"))
	_stage.add_child(architecture)
	_stage.add_child(_trust_pill(Vector2(x, top + 685), Vector2(size.x - 32, 48)))
	_build_lower_sections(top + 800, x, size.x - 32, true)

func _build_launcher(pos: Vector2, launcher_size: Vector2) -> void:
	var card := _panel(pos, launcher_size, Color("f4f8fb"), 22, Color("cbd7e7"), 1, Color(0.18, 0.12, 0.24, 0.10), 16)
	_stage.add_child(card)
	var back := _panel(Vector2(-22, 15), Vector2(launcher_size.x - 24, launcher_size.y - 28), Color(1,1,1,0.38), 18, Color("d8cae8"), 1, Color(0.18,0.12,0.24,0.06), 8)
	back.rotation_degrees = -1.4
	card.add_child(back)
	card.move_child(back, 0)

	var hint := _panel(Vector2(15, 32), Vector2(250, 56), C.editorial_soft, 14, Color("efc6d8"), 1)
	var hint_text := _label("Let’s weave something lovely today (｡•̀ᴗ-)✧" if _locale == "en-US" else "今天也把故事织得更漂亮一点吧 (｡•̀ᴗ-)✧", 12, 480, C.editorial)
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

	var search := _panel(Vector2(15, 99), Vector2(launcher_size.x - 30, 49), Color("fffdf9"), 13, Color("ead4c4"), 1)
	var search_label := _label("⌕  Search product, docs, architecture, publication…" if _locale == "en-US" else "⌕  搜索产品、文档、架构、出版…", 14, 430, C.muted)
	search_label.position = Vector2(13, 13)
	search_label.size = Vector2(launcher_size.x - 180, 25)
	search.add_child(search_label)
	var shortcut := _label("⌘K / Ctrl+K", 12, 560, C.muted)
	shortcut.position = Vector2(launcher_size.x - 150, 14)
	shortcut.size = Vector2(120, 22)
	search.add_child(shortcut)
	card.add_child(search)

	var gap := 12.0
	var tile_w := (launcher_size.x - 42.0) / 2.0
	var tile_h := 82.0
	var tile_y := 162.0
	card.add_child(_launcher_tile(Vector2(15, tile_y), Vector2(tile_w, tile_h), "✦", "Studio", "Start operating" if _locale == "en-US" else "真正开始操作", C.runtime_soft, Color("cfc3ee"), true))
	card.add_child(_launcher_tile(Vector2(15 + tile_w + gap, tile_y), Vector2(tile_w, tile_h), "♡", "Product" if _locale == "en-US" else "产品能力", "See what it solves" if _locale == "en-US" else "看它解决什么", C.editorial_soft, Color("f0cedd"), false))
	card.add_child(_launcher_tile(Vector2(15, tile_y + tile_h + gap), Vector2(tile_w, tile_h), "📚", "Knowledge" if _locale == "en-US" else "知识库", "Search real docs" if _locale == "en-US" else "搜索真实文档", C.evidence_soft, Color("eddcbb"), false))
	card.add_child(_launcher_tile(Vector2(15 + tile_w + gap, tile_y + tile_h + gap), Vector2(tile_w, tile_h), "✧", "Publication" if _locale == "en-US" else "出版", "Accepted text to formats" if _locale == "en-US" else "从接受稿到派生格式", C.valid_soft, Color("cde7dd"), false))
	var footer := _label("0.8.x                                      pre-1.0 · actively evolving                                      authority=false" if _locale == "en-US" else "0.8.x                                      pre-1.0 · 快速演进                                      authority=false", 10, 480, Color("857c8b"))
	footer.position = Vector2(15, launcher_size.y - 51)
	footer.size = Vector2(launcher_size.x - 30, 24)
	card.add_child(footer)

func _launcher_tile(pos: Vector2, tile_size: Vector2, icon: String, title: String, note: String, bg: Color, border: Color, external: bool) -> Panel:
	var tile := _panel(pos, tile_size, bg, 16, border, 1, Color(0.18, 0.12, 0.24, 0.05), 5)
	var icon_box := _panel(Vector2(12, 18), Vector2(42, 42), Color(1,1,1,0.56), 12)
	if icon == "📚":
		var books := TextureRect.new()
		books.texture = _books_icon
		books.position = Vector2(11, 11)
		books.size = Vector2(20, 20)
		books.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		books.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		books.mouse_filter = Control.MOUSE_FILTER_IGNORE
		icon_box.add_child(books)
	else:
		var icon_label := _label(icon, 20, 650, C.runtime if title == "Studio" else C.editorial)
		icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		icon_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		icon_box.add_child(icon_label)
	tile.add_child(icon_box)
	var title_label := _label(title, 16, 720, C.ink)
	title_label.position = Vector2(66, 18)
	title_label.size = Vector2(tile_size.x - 100, 24)
	tile.add_child(title_label)
	var note_label := _label(note, 11, 430, C.muted)
	note_label.position = Vector2(66, 43)
	note_label.size = Vector2(tile_size.x - 100, 22)
	tile.add_child(note_label)
	var arrow := _label("↗" if external else "→", 16, 700, C.ink)
	arrow.position = Vector2(tile_size.x - 30, 29)
	arrow.size = Vector2(18, 22)
	tile.add_child(arrow)
	return tile

func _build_lower_sections(y: float, x: float, width: float, phone: bool) -> void:
	var kicker := _label("✦  Six real product capabilities" if _locale == "en-US" else "✦  六条真实产品能力", 12, 720, C.runtime)
	kicker.position = Vector2(x, y)
	kicker.size = Vector2(width, 26)
	_stage.add_child(kicker)
	var section_title := _label("Touch the boundaries, not another feature wall." if _locale == "en-US" else "直接触碰系统边界，而不是再看一面 feature wall。", 31 if not phone else 27, 760, C.ink)
	section_title.position = Vector2(x, y + 34)
	section_title.size = Vector2(width, 74)
	section_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_stage.add_child(section_title)
	var cards := [
		["Context", "What reaches the model is budgeted and visible.", C.project_soft, Color("bedfec")],
		["Readiness", "Required evidence stays bound to one candidate.", C.editorial_soft, Color("f0ccdc")],
		["Authority", "Capability never silently becomes write authority.", C.evidence_soft, Color("edddb8")],
	]
	if phone:
		var cy := y + 120
		for item in cards:
			_stage.add_child(_info_card(Vector2(x, cy), Vector2(width, 150), str(item[0]), str(item[1]), item[2], item[3]))
			cy += 164
	else:
		var card_w := (width - 28) / 3.0
		for i in range(cards.size()):
			var item = cards[i]
			_stage.add_child(_info_card(Vector2(x + i * (card_w + 14), y + 126), Vector2(card_w, 176), str(item[0]), str(item[1]), item[2], item[3]))

func _info_card(pos: Vector2, card_size: Vector2, title: String, body: String, bg: Color, border: Color) -> Panel:
	var card := _panel(pos, card_size, bg, 20, border, 1)
	var title_label := _label(title, 19, 740, C.ink)
	title_label.position = Vector2(18, 18)
	title_label.size = Vector2(card_size.x - 36, 28)
	card.add_child(title_label)
	var body_label := _label(body, 14, 430, C.muted)
	body_label.position = Vector2(18, 57)
	body_label.size = Vector2(card_size.x - 36, card_size.y - 75)
	body_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(body_label)
	return card

func _trust_pill(pos: Vector2, pill_size: Vector2) -> Panel:
	var pill := _panel(pos, pill_size, Color("fbfcfa"), int(pill_size.y / 2.0), Color("d9e7dd"), 1)
	var dot := ColorRect.new()
	dot.color = C.valid
	dot.position = Vector2(12, pill_size.y / 2.0 - 4)
	dot.size = Vector2(8, 8)
	pill.add_child(dot)
	var text := _label("Product claims map to contracts that exist on current main" if _locale == "en-US" else "产品主张来自 current main 已存在的契约", 11, 460, C.muted)
	text.position = Vector2(27, 9 if pill_size.y < 42 else 8)
	text.size = Vector2(pill_size.x - 37, pill_size.y - 12)
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	pill.add_child(text)
	return pill

func _panel(pos: Vector2, panel_size: Vector2, bg: Color, radius: int, border: Color = Color(0,0,0,0), border_width: int = 0, shadow: Color = Color(0,0,0,0), shadow_size: int = 0) -> Panel:
	var panel := Panel.new()
	panel.position = pos
	panel.size = panel_size
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	if border_width > 0:
		style.border_color = border
		style.border_width_left = border_width
		style.border_width_top = border_width
		style.border_width_right = border_width
		style.border_width_bottom = border_width
	if shadow_size > 0:
		style.shadow_color = shadow
		style.shadow_size = shadow_size
		style.shadow_offset = Vector2(0, max(2, shadow_size / 3))
	panel.add_theme_stylebox_override("panel", style)
	return panel

func _pill(text: String, pos: Vector2, pill_size: Vector2, bg: Color, fg: Color, font_size: int, weight: int, border: Color = Color(0,0,0,0)) -> Panel:
	var panel := _panel(pos, pill_size, bg, int(pill_size.y / 2.0), border, 1 if border.a > 0.0 else 0)
	var label := _label(text, font_size, weight, fg)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	panel.add_child(label)
	return panel

func _label(text: String, font_size: int, weight: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_override("font", _font(weight))
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label

func _text_button(text: String, pos: Vector2, button_size: Vector2, bg: Color, fg: Color, font_size: int, weight: int, radius: int) -> Button:
	var button := Button.new()
	button.text = text
	button.position = pos
	button.size = button_size
	button.focus_mode = Control.FOCUS_ALL
	button.add_theme_font_override("font", _font(weight))
	button.add_theme_font_size_override("font_size", font_size)
	button.add_theme_color_override("font_color", fg)
	button.add_theme_color_override("font_hover_color", fg)
	button.add_theme_color_override("font_pressed_color", fg)
	button.add_theme_stylebox_override("normal", _button_box(bg, radius))
	button.add_theme_stylebox_override("hover", _button_box(bg.lightened(0.025) if bg.a > 0.0 else Color(0.48,0.42,0.77,0.08), radius))
	button.add_theme_stylebox_override("pressed", _button_box(bg.darkened(0.04) if bg.a > 0.0 else Color(0.48,0.42,0.77,0.12), radius))
	button.add_theme_stylebox_override("focus", _focus_box(radius))
	return button

func _button_box(bg: Color, radius: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	style.content_margin_left = 10
	style.content_margin_right = 10
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	if bg.a > 0.0:
		style.shadow_color = Color(0.20,0.13,0.28,0.08)
		style.shadow_size = 4
		style.shadow_offset = Vector2(0, 3)
	return style

func _focus_box(radius: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0,0,0,0)
	style.border_color = C.runtime
	style.border_width_left = 2
	style.border_width_top = 2
	style.border_width_right = 2
	style.border_width_bottom = 2
	style.corner_radius_top_left = radius + 2
	style.corner_radius_top_right = radius + 2
	style.corner_radius_bottom_left = radius + 2
	style.corner_radius_bottom_right = radius + 2
	style.expand_margin_left = 2
	style.expand_margin_top = 2
	style.expand_margin_right = 2
	style.expand_margin_bottom = 2
	return style

func _toggle_locale() -> void:
	_locale = "zh-CN" if _locale == "en-US" else "en-US"
	if OS.has_feature("web"):
		JavaScriptBridge.eval("localStorage.setItem('novelforge.locale', '%s')" % _locale)
	_build()

func _navigate(path: String) -> void:
	if not OS.has_feature("web"):
		return
	if path.begins_with("/docs"):
		JavaScriptBridge.eval("window.location.assign('%s')" % path)
	else:
		JavaScriptBridge.eval("window.history.pushState({}, '', '%s'); window.dispatchEvent(new PopStateEvent('popstate'));" % path)

func _open_external(url: String) -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.open('%s', '_blank', 'noopener,noreferrer')" % url)

func _publish_ready() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("document.documentElement.dataset.novelforgeLayout='%s'; document.documentElement.dataset.novelforgeRuntime='ready'; window.dispatchEvent(new CustomEvent('novelforge:godot-ready'));" % _layout)

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), C.bg)
	_soft_circle(Vector2(size.x * 0.78, 150), min(size.x * 0.34, 470.0), Color(0.95,0.76,0.86,0.055))
	_soft_circle(Vector2(size.x * 0.12, 220), min(size.x * 0.28, 390.0), Color(0.63,0.82,0.94,0.05))
	_soft_circle(Vector2(size.x * 0.57, 560), min(size.x * 0.32, 430.0), Color(0.56,0.49,0.83,0.035))
	var stripe_y := 63.0
	var stripe_colors := [C.project, C.runtime, C.editorial, C.evidence, C.valid]
	var stripe_x := 42.0 if _layout == "desktop" else 30.0
	for i in range(18):
		var col: Color = stripe_colors[i % stripe_colors.size()]
		col.a = 0.35
		draw_rect(Rect2(Vector2(stripe_x + i * 17.0, stripe_y), Vector2(9.0, 4.0)), col)

func _soft_circle(center: Vector2, radius: float, color: Color) -> void:
	for i in range(10, 0, -1):
		var factor := float(i) / 10.0
		var layer := color
		layer.a = color.a * (1.0 - factor * 0.68)
		draw_circle(center, radius * factor, layer)
