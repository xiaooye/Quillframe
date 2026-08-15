extends "res://scripts/main.gd"

const LAUNCHER_CONTENT_INSET := 36.0
const LAUNCHER_CONTENT_GAP := 12.0
const MOBILE_LEDE_LINE_SPACING := 3
const DESKTOP_LEDE_LINE_SPACING := 4

const PRODUCT_CARDS_EN := [
	["Authority before convenience", "Locked, accepted, active plan, review, proposal, derived, runtime, learning, and corpus material are not interchangeable."],
	["Evidence before confidence", "Context and character decisions can expose exactly what support existed, what was eligible, and what actually entered the active packet."],
	["Repair the owning mechanism", "Surface clusters regenerate scenes; reader-grip failures return to Reader Pressure and Scene Simulation; story failures return to Story mechanics."],
	["Acceptance is a real boundary", "A review candidate is not Canon. User acceptance and exact settlement remain explicit transitions with fingerprints and before/after evidence."],
]

const PRODUCT_CARDS_ZH := [
	["权威先于方便", "锁定内容、已接受内容、当前计划、审查稿、提案、派生状态、运行状态、学习材料和语料材料不能混成一层“记忆”。"],
	["证据先于自信", "上下文与角色决策都可以说明：有哪些依据、哪些依据在当前阶段有效、最后哪些真的进入了活动上下文包。"],
	["问题回到真正负责它的机制", "文本表面问题回到整场景修复；读者抓力问题回到读者压力与场景模拟；故事问题回到故事机制。"],
	["接受是一道真正的边界", "进入审查的候选稿还不是正典。用户接受与精确结算都是显式转换，并绑定指纹和修改前后的证据。"],
]

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
	var route := _current_route()
	var stage_height := 1760.0 if _layout == "desktop" else (1580.0 if _layout == "compact" else 1750.0)
	if route == "/product":
		stage_height = 1120.0 if _layout == "desktop" else (1280.0 if _layout == "compact" else 1640.0)
	_stage.custom_minimum_size = Vector2(max(size.x, 320.0), stage_height)
	_scroll.add_child(_stage)

	if route == "/product":
		_build_product_route()
	elif _layout == "desktop":
		_build_desktop()
	elif _layout == "compact":
		_build_compact()
	else:
		_build_phone()
	_build_header()
	_style_scrollbar()

func _current_route() -> String:
	if not OS.has_feature("web"):
		return "/"
	var value = JavaScriptBridge.eval("(() => { const q=new URLSearchParams(location.search).get('route'); return q || location.pathname || '/'; })()")
	if typeof(value) == TYPE_STRING:
		var route := str(value)
		return route if route != "" else "/"
	return "/"

func _navigate(path: String) -> void:
	if not OS.has_feature("web"):
		return
	if path.begins_with("/docs"):
		JavaScriptBridge.eval("window.location.assign('%s')" % path)
		return
	JavaScriptBridge.eval("window.history.pushState({}, '', '%s');" % path)
	_build()
	_publish_ready()

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
	if get_child_count() == 0:
		return
	var header := get_child(get_child_count() - 1)
	if not header is Panel:
		return
	var route := _current_route()
	for child in header.get_children():
		if child is Button:
			var button := child as Button
			if route == "/product" and button.text == "Product":
				button.add_theme_color_override("font_color", C.runtime)
				button.add_theme_color_override("font_hover_color", C.runtime)
				button.add_theme_stylebox_override("normal", _button_box(Color("f2eefb"), 10))
			if _layout == "phone":
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

func _build_product_route() -> void:
	if _layout == "desktop":
		_build_product_desktop()
	elif _layout == "compact":
		_build_product_compact()
	else:
		_build_product_phone()

func _build_product_desktop() -> void:
	var page_x := 70.0
	var page_width := size.x - 140.0
	var hero_y := 122.0
	var hero_h := 483.0
	_build_product_hero(Vector2(page_x, hero_y), Vector2(page_width, hero_h), false)
	_build_product_cards(Vector2(page_x, 638.0), page_width, false)

func _build_product_compact() -> void:
	var page_x := 40.0
	var page_width := size.x - 80.0
	var hero_y := 112.0
	var hero_h := 720.0
	_build_product_hero(Vector2(page_x, hero_y), Vector2(page_width, hero_h), true)
	_build_product_cards(Vector2(page_x, 860.0), page_width, false)

func _build_product_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero_y := 89.0
	var hero_h := 780.0
	_build_product_hero(Vector2(page_x, hero_y), Vector2(page_width, hero_h), true)
	_build_product_cards(Vector2(page_x, 895.0), page_width, true)

func _build_product_hero(pos: Vector2, hero_size: Vector2, stacked: bool) -> void:
	var hero := _panel(pos, hero_size, Color("fffdfc"), 28 if not stacked else 22, Color("e8ddea"), 1, Color(0.18,0.12,0.24,0.10), 14)
	_stage.add_child(hero)
	var inner := _panel(Vector2(8 if not stacked else 6, 8 if not stacked else 6), hero_size - Vector2(16 if not stacked else 12, 16 if not stacked else 12), Color(0,0,0,0), 20 if not stacked else 16, Color(0.95,0.74,0.84,0.32), 1)
	inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hero.add_child(inner)

	var pad := 48.0 if not stacked else 18.0
	var eyebrow := _label("PRODUCT MODEL" if _locale == "en-US" else "产品模型", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, pad + 1)
	eyebrow.size = Vector2(240, 22)
	hero.add_child(eyebrow)

	var title_text := ""
	var title_size := 62
	var title_box := Vector2(610, 260)
	var title_y := pad + 28.0
	if _locale == "zh-CN":
		title_text = "NovelForge 是小说生产系统，\n不是提示词外壳。" if not stacked else "NovelForge 是小说\n生产系统，不是\n提示词外壳。"
		title_size = 54 if not stacked else 42
		title_box = Vector2(610 if not stacked else hero_size.x - pad * 2.0, 190 if not stacked else 150)
	else:
		title_text = "NovelForge is a\nfiction production\nsystem, not a\nprompt wrapper." if not stacked else "NovelForge\nis a fiction\nproduction\nsystem, not\na prompt\nwrapper."
		title_size = 62 if not stacked else 46
		title_box = Vector2(610 if not stacked else hero_size.x - pad * 2.0, 260 if not stacked else 240)
	var title := _label(title_text, title_size, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, title_y)
	title.size = title_box
	title.scale = Vector2(1.025 if _locale == "en-US" else 1.0, 1.0)
	title.add_theme_constant_override("line_spacing", -28 if not stacked and _locale == "en-US" else (-20 if stacked and _locale == "en-US" else -10))
	hero.add_child(title)

	var lede_text := ""
	if _locale == "zh-CN":
		lede_text = "它把创作判断与确定性控制分开，让一本长期运行的书能持续积累证据、\n修订和状态，而不是把每一次模型输出都顺手升级成事实。" if not stacked else "它把创作判断与确定性控制分开，让一本长期运行的书能持续积累证据、修订和状态，而不是把每一次模型输出都顺手升级成事实。"
	else:
		lede_text = "It separates creative judgment from deterministic control so a long-\nrunning book can accumulate evidence, revisions, and state without\nturning every previous model output into truth." if not stacked else "It separates creative judgment from\ndeterministic control so a long-running\nbook can accumulate evidence, revisions,\nand state without turning every previous\nmodel output into truth."
	var lede := _label(lede_text, 17 if not stacked else 16, 420, C.muted)
	lede.position = Vector2(pad, 350.0 if not stacked else 310.0)
	if stacked and _locale == "en-US":
		lede.position.y = 310.0
	elif stacked:
		lede.position.y = 220.0
	lede.size = Vector2(610 if not stacked else hero_size.x - pad * 2.0, 150)
	lede.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lede.add_theme_constant_override("line_spacing", 4 if not stacked else 3)
	hero.add_child(lede)

	if not stacked:
		var inner_width := hero_size.x - pad * 2.0
		var gap := 54.0
		var available := inner_width - gap
		var copy_w := available * 1.05 / 2.0
		var visual_w := available - copy_w
		_build_product_stack(hero, Vector2(pad + copy_w + gap, pad), Vector2(visual_w, hero_size.y - pad * 2.0), false)
	else:
		var visual_y := 454.0 if _locale == "en-US" else 370.0
		_build_product_stack(hero, Vector2(pad, visual_y), Vector2(hero_size.x - pad * 2.0, 300.0), true)

func _build_product_stack(parent: Control, pos: Vector2, stack_size: Vector2, phone: bool) -> void:
	var stack := _panel(pos, stack_size, Color("fbf9fd"), 22, Color("eee5f0"), 1, Color(0.18,0.12,0.24,0.05), 6)
	parent.add_child(stack)
	var tag := _panel(Vector2(stack_size.x - 122, 13), Vector2(108, 30), C.editorial_soft, 9, Color("efc8d9"), 1, Color(0.18,0.12,0.24,0.05), 4)
	var tag_text := _label("♡ STORY STATE", 9, 760, C.editorial)
	tag_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tag_text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	tag_text.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	tag.add_child(tag_text)
	stack.add_child(tag)

	var names := ["Canon", "Context", "Evidence", "Candidate", "Settlement"]
	var shifts := [0.0, 14.0, 28.0, 14.0, 0.0]
	var row_x := 50.0 if not phone else 18.0
	var row_y := 64.0 if not phone else 18.0
	var row_h := 47.0
	var row_gap := 7.0
	var base_w := stack_size.x - (100.0 if not phone else 36.0)
	for i in range(names.size()):
		var shift: float = shifts[i]
		var row := _panel(Vector2(row_x + shift, row_y + i * (row_h + row_gap)), Vector2(base_w - shift, row_h), Color("fffdfc"), 12, Color("e7deea"), 1, Color(0.18,0.12,0.24,0.05), 4)
		var dot := ColorRect.new()
		dot.color = C.editorial
		dot.position = Vector2(0, row_h / 2.0 - 4)
		dot.size = Vector2(8, 8)
		row.add_child(dot)
		var text := _label(str(names[i]), 14 if not phone else 13, 720, C.ink)
		text.position = Vector2(17, 12)
		text.size = Vector2(row.size.x - 30, 24)
		row.add_child(text)
		stack.add_child(row)

func _build_product_cards(pos: Vector2, width: float, phone: bool) -> void:
	var cards = PRODUCT_CARDS_ZH if _locale == "zh-CN" else PRODUCT_CARDS_EN
	var fills := [Color("fffafd"), Color("fffaf9"), Color("fbfdfb"), Color("fffdf9")]
	if phone:
		var y := pos.y
		for i in range(cards.size()):
			_stage.add_child(_product_card(Vector2(pos.x, y), Vector2(width, 164), i, str(cards[i][0]), str(cards[i][1]), fills[i]))
			y += 178.0
	else:
		var gap := 13.0
		var card_w := (width - gap * 2.0) / 3.0
		for i in range(cards.size()):
			var row := 0 if i < 3 else 1
			var col := i if i < 3 else 0
			var card_pos := Vector2(pos.x + col * (card_w + gap), pos.y + row * 200.0)
			_stage.add_child(_product_card(card_pos, Vector2(card_w, 188), i, str(cards[i][0]), str(cards[i][1]), fills[i]))

func _product_card(pos: Vector2, card_size: Vector2, index: int, title_text: String, body_text: String, bg: Color) -> Panel:
	var card := _panel(pos, card_size, bg, 20, Color("e8ddea"), 1)
	var index_label := _label("%02d" % (index + 1), 10, 760, C.runtime)
	index_label.position = Vector2(20, 22)
	index_label.size = Vector2(44, 20)
	card.add_child(index_label)
	var title := _label(title_text, 19, 740, C.ink)
	title.position = Vector2(20, 53)
	title.size = Vector2(card_size.x - 40, 32)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(title)
	var body := _label(body_text, 13, 430, C.muted)
	body.position = Vector2(20, 94)
	body.size = Vector2(card_size.x - 40, card_size.y - 108)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_theme_constant_override("line_spacing", 5)
	card.add_child(body)
	return card

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
