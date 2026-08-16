extends "res://scripts/system_surfaces.gd"

const EDITORIAL_STAGE_HEIGHTS := {
	"/architecture": {"desktop": 1220.0, "compact": 1460.0, "phone": 1700.0},
	"/publication": {"desktop": 1320.0, "compact": 1540.0, "phone": 1860.0},
}

func _build() -> void:
	var route := _current_route()
	if not EDITORIAL_STAGE_HEIGHTS.has(route):
		super._build()
		return
	_build_editorial_route(route)

func _build_editorial_route(route: String) -> void:
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
	var heights: Dictionary = EDITORIAL_STAGE_HEIGHTS[route]
	_stage.custom_minimum_size = Vector2(max(size.x, 320.0), float(heights[_layout]))
	_scroll.add_child(_stage)
	match route:
		"/architecture": _build_architecture_route()
		"/publication": _build_publication_route()
	_build_header()
	_style_scrollbar()

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
			if (route == "/architecture" and button.text == "Architecture") or (route == "/publication" and button.text == "Publication"):
				button.add_theme_color_override("font_color", C.runtime)
				button.add_theme_color_override("font_hover_color", C.runtime)
				button.add_theme_stylebox_override("normal", _button_box(C.runtime_soft, 10))

func _build_architecture_route() -> void:
	if _layout == "phone":
		_build_architecture_phone()
	else:
		_build_architecture_desktop(_layout == "compact")

func _build_architecture_desktop(compact: bool) -> void:
	var page_x := 40.0 if compact else 70.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 110.0 if compact else 122.0
	var hero_h := 520.0 if compact else 461.0
	var hero := _route_hero_panel(Vector2(page_x, hero_y), Vector2(page_width, hero_h), 28)
	var pad := 44.0
	var ornament := _mixed_label("☁   ✦   · · · · ·   →   ◇   →   ♡   →   ✧", 16, 600, Color("dfcaed"))
	ornament.position = Vector2(12, 15)
	ornament.size = Vector2(430, 24)
	hero.add_child(ornament)
	var eyebrow := _label("INTERACTIVE ARCHITECTURE" if _locale == "en-US" else "交互式架构", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, 43)
	eyebrow.size = Vector2(260, 22)
	hero.add_child(eyebrow)
	hero.add_child(_pill("authority=false", Vector2(pad, 70), Vector2(112, 28), C.evidence_soft, C.ink, 12, 520, Color("eadfc4")))
	var title_text := "See how one\nNovelForge run moves\nthrough the system." if _locale == "en-US" else "看一次 NovelForge\n运行如何穿过\n整个系统。"
	var title := _label(title_text, 62 if _locale == "en-US" else 52, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, 106)
	title.size = Vector2(660, 205)
	title.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -9)
	hero.add_child(title)
	var lede_text := "Project → Manager → Context → Worker → Gate → Settlement → Publication. One\nproduct shell, with each node owning only its mechanism boundary." if _locale == "en-US" else "Project → Manager → Context → Worker → Gate → Settlement → Publication。\n同一个产品壳，但每个节点只拥有自己的机制边界。"
	var lede := _label(lede_text, 17, 420, C.muted)
	lede.position = Vector2(pad, 305 if _locale == "en-US" else 260)
	lede.size = Vector2(650, 72)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	var docs := _mixed_text_button("📚 Read architecture docs" if _locale == "en-US" else "📚 阅读架构文档", Vector2(pad, 382 if _locale == "en-US" else 345), Vector2(220, 44), C.runtime_soft, C.runtime, 14, 600, 8)
	docs.icon = _books_icon
	docs.pressed.connect(_navigate.bind("/docs"))
	hero.add_child(docs)
	var play := _text_button("▷ Playground", Vector2(pad + 236, 382 if _locale == "en-US" else 345), Vector2(150, 44), Color(0,0,0,0), C.runtime, 14, 560, 8)
	play.pressed.connect(_navigate.bind("/playground"))
	hero.add_child(play)
	_build_architecture_grid(hero, Vector2(page_width * 0.59, 43), Vector2(page_width * 0.38, hero_h - 86), false)
	_build_execution_path(Vector2(page_x, hero_y + hero_h + 32), Vector2(page_width, 360), false)

func _build_architecture_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero := _route_hero_panel(Vector2(page_x, 89), Vector2(page_width, 1040), 22)
	var eyebrow := _label("INTERACTIVE ARCHITECTURE" if _locale == "en-US" else "交互式架构", 11, 820, C.editorial)
	eyebrow.position = Vector2(18, 23)
	eyebrow.size = Vector2(260, 22)
	hero.add_child(eyebrow)
	hero.add_child(_pill("authority=false", Vector2(18, 50), Vector2(112, 28), C.evidence_soft, C.ink, 12, 520, Color("eadfc4")))
	var title_text := "See how one\nNovelForge run\nmoves through\nthe system." if _locale == "en-US" else "看一次 NovelForge\n运行如何穿过\n整个系统。"
	var title := _label(title_text, 39, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(18, 88)
	title.size = Vector2(page_width - 36, 185)
	title.add_theme_constant_override("line_spacing", -18 if _locale == "en-US" else -8)
	hero.add_child(title)
	var lede_text := "Project → Manager → Context → Worker →\nGate → Settlement → Publication. One\nproduct shell, with each node owning only\nits mechanism boundary." if _locale == "en-US" else "Project → Manager → Context → Worker → Gate →\nSettlement → Publication。每个节点只拥有\n自己的机制边界。"
	var lede := _label(lede_text, 16, 420, C.muted)
	lede.position = Vector2(18, 273 if _locale == "en-US" else 230)
	lede.size = Vector2(page_width - 36, 150)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	var docs := _mixed_text_button("📚 Read architecture docs" if _locale == "en-US" else "📚 阅读架构文档", Vector2(18, 397 if _locale == "en-US" else 350), Vector2(220, 44), C.runtime_soft, C.runtime, 14, 600, 8)
	docs.icon = _books_icon
	docs.pressed.connect(_navigate.bind("/docs"))
	hero.add_child(docs)
	var play := _text_button("▷ Playground", Vector2(18, 452 if _locale == "en-US" else 405), Vector2(150, 38), Color(0,0,0,0), C.runtime, 14, 560, 8)
	play.pressed.connect(_navigate.bind("/playground"))
	hero.add_child(play)
	_build_architecture_grid(hero, Vector2(18, 495 if _locale == "en-US" else 450), Vector2(page_width - 36, 520), true)
	_build_execution_path(Vector2(page_x, 1155), Vector2(page_width, 480), true)

func _build_architecture_grid(parent: Control, pos: Vector2, grid_size: Vector2, phone: bool) -> void:
	var grid := _panel(pos, grid_size, Color("fffdfc"), 18, Color("cfc3ee"), 1)
	parent.add_child(grid)
	for x in range(0, int(grid_size.x), 22):
		var v := ColorRect.new()
		v.color = Color(0.47,0.42,0.77,0.09)
		v.position = Vector2(x, 0)
		v.size = Vector2(1, grid_size.y)
		grid.add_child(v)
	for y in range(0, int(grid_size.y), 22):
		var h := ColorRect.new()
		h.color = Color(0.47,0.42,0.77,0.09)
		h.position = Vector2(0, y)
		h.size = Vector2(grid_size.x, 1)
		grid.add_child(h)
	var names := ["Project", "Manager", "Context", "Worker", "Gate", "Settlement", "Publication"]
	var icons := ["⌂", "✦", "◉", "⌘", "✓", "◇", "▤"]
	var cols := 2 if phone else 7
	var gap := 8.0
	var cell_w := (grid_size.x - 48.0 - gap * (cols - 1)) / cols
	var cell_h := 74.0 if phone else 92.0
	var start_y := 24.0 if phone else grid_size.y / 2.0 - cell_h / 2.0
	for i in range(names.size()):
		var col := i % cols
		var row := i / cols
		var cell := _panel(Vector2(24 + col * (cell_w + gap), start_y + row * (cell_h + gap)), Vector2(cell_w, cell_h), Color("fffdfc"), 13, Color("e4dbe9"), 1)
		if i == 0:
			cell.add_theme_stylebox_override("panel", _button_box(C.runtime_soft, 13))
		var icon := _mixed_label(str(icons[i]), 18, 700, C.ink)
		icon.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		icon.position = Vector2(0, 14)
		icon.size = Vector2(cell_w, 25)
		cell.add_child(icon)
		var name := _label(str(names[i]), 10 if not phone else 12, 700, C.ink)
		name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name.position = Vector2(0, 43)
		name.size = Vector2(cell_w, 22)
		cell.add_child(name)
		grid.add_child(cell)

func _build_execution_path(pos: Vector2, board_size: Vector2, phone: bool) -> void:
	var board := _panel(pos, board_size, Color("fffdfc"), 24, Color("d7cdef"), 1)
	_stage.add_child(board)
	var eyebrow := _label("OBSERVABLE EXECUTION PATH", 10, 760, C.muted)
	eyebrow.position = Vector2(20, 20)
	eyebrow.size = Vector2(250, 20)
	board.add_child(eyebrow)
	var title := _label("Select a node or start a preview" if _locale == "en-US" else "选择节点或启动预览", 14, 650, C.ink)
	title.position = Vector2(20, 43)
	title.size = Vector2(330, 24)
	board.add_child(title)
	var simulate := _text_button("Simulate a run" if _locale == "en-US" else "模拟一次运行", Vector2(board_size.x - 260, 17), Vector2(155, 44), C.runtime, Color.WHITE, 14, 600, 8)
	board.add_child(simulate)
	var reset := _text_button("Reset", Vector2(board_size.x - 95, 17), Vector2(75, 44), Color(0,0,0,0), C.runtime, 14, 560, 8)
	board.add_child(reset)
	var names := ["Project", "Manager", "Context", "Worker", "Gate", "Settlement", "Publication"]
	if phone:
		var y := 88.0
		for i in range(names.size()):
			var row := _panel(Vector2(20, y), Vector2(board_size.x - 40, 48), Color("fffdfc"), 12, Color("e7deea"), 1)
			var text := _label("%02d   %s" % [i + 1, names[i]], 13, 650, C.ink)
			text.position = Vector2(14, 13)
			text.size = Vector2(row.size.x - 28, 24)
			row.add_child(text)
			board.add_child(row)
			y += 55.0
	else:
		var gap := 10.0
		var cell_w := (board_size.x - 40 - gap * 6) / 7.0
		for i in range(names.size()):
			var cell := _panel(Vector2(20 + i * (cell_w + gap), 95), Vector2(cell_w, 220), Color("fffdfc"), 14, Color("e7deea"), 1)
			var idx := _pill("%02d" % (i + 1), Vector2(12, 14), Vector2(38, 34), C.runtime_soft, C.muted, 9, 650)
			cell.add_child(idx)
			var name := _label(str(names[i]), 14, 720, C.ink)
			name.position = Vector2(12, 65)
			name.size = Vector2(cell_w - 24, 28)
			cell.add_child(name)
			board.add_child(cell)

func _build_publication_route() -> void:
	if _layout == "phone":
		_build_publication_phone()
	else:
		_build_publication_desktop(_layout == "compact")

func _build_publication_desktop(compact: bool) -> void:
	var page_x := 40.0 if compact else 70.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 110.0 if compact else 122.0
	var hero_h := 570.0 if compact else 525.0
	var hero := _route_hero_panel(Vector2(page_x, hero_y), Vector2(page_width, hero_h), 28)
	var pad := 44.0
	var eyebrow := _mixed_label("🎀 PUBLICATION WORKBENCH" if _locale == "en-US" else "🎀 出版工作台", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, 43)
	eyebrow.size = Vector2(280, 22)
	hero.add_child(eyebrow)
	hero.add_child(_pill("deterministic", Vector2(pad, 70), Vector2(96, 28), Color("fffdfc"), C.ink, 12, 520, Color("e2dae7")))
	hero.add_child(_pill("authority=false", Vector2(pad + 106, 70), Vector2(112, 28), Color("fffdfc"), C.ink, 12, 520, Color("e2dae7")))
	var black := _label("One accepted\nmanuscript," if _locale == "en-US" else "一份已接受稿，", 62 if _locale == "en-US" else 52, 780 if _locale == "en-US" else 720, C.ink)
	black.position = Vector2(pad, 108)
	black.size = Vector2(510, 140)
	black.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -8)
	hero.add_child(black)
	var pink := _label("many\ndeterministic\nderivatives." if _locale == "en-US" else "确定性地产生\n多种派生格式。", 62 if _locale == "en-US" else 52, 780 if _locale == "en-US" else 720, Color("e94c9a"))
	pink.position = Vector2(pad, 241 if _locale == "en-US" else 190)
	pink.size = Vector2(520, 210)
	pink.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -8)
	hero.add_child(pink)
	var lede := _label("One Publication IR produces TXT, Web, Print, and EPUB.\nPresentation changes; manuscript truth does not." if _locale == "en-US" else "一份 Publication IR 生成 TXT、Web、Print 与 EPUB。\n展示会变，稿件事实不会。", 17, 420, C.muted)
	lede.position = Vector2(pad, 430 if _locale == "en-US" else 340)
	lede.size = Vector2(520, 75)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_format_showcase(hero, Vector2(page_width * 0.47, 43), Vector2(page_width * 0.50, hero_h - 86), false)
	_build_format_strip(Vector2(page_x, hero_y + hero_h + 32), Vector2(page_width, 118), false)
	_build_reading_preview(Vector2(page_x, hero_y + hero_h + 182), Vector2(page_width, 360), false)

func _build_publication_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero := _route_hero_panel(Vector2(page_x, 89), Vector2(page_width, 1160), 22)
	var eyebrow := _mixed_label("🎀 PUBLICATION WORKBENCH" if _locale == "en-US" else "🎀 出版工作台", 11, 820, C.editorial)
	eyebrow.position = Vector2(18, 23)
	eyebrow.size = Vector2(280, 22)
	hero.add_child(eyebrow)
	hero.add_child(_pill("deterministic", Vector2(18, 50), Vector2(96, 28), Color("fffdfc"), C.ink, 12, 520, Color("e2dae7")))
	hero.add_child(_pill("authority=false", Vector2(124, 50), Vector2(112, 28), Color("fffdfc"), C.ink, 12, 520, Color("e2dae7")))
	var black := _label("One accepted\nmanuscript," if _locale == "en-US" else "一份已接受稿，", 39, 780 if _locale == "en-US" else 720, C.ink)
	black.position = Vector2(18, 88)
	black.size = Vector2(page_width - 36, 95)
	black.add_theme_constant_override("line_spacing", -18)
	hero.add_child(black)
	var pink := _label("many\ndeterministic\nderivatives." if _locale == "en-US" else "确定性地产生\n多种派生格式。", 39, 780 if _locale == "en-US" else 720, Color("e94c9a"))
	pink.position = Vector2(18, 176 if _locale == "en-US" else 150)
	pink.size = Vector2(page_width - 36, 160)
	pink.add_theme_constant_override("line_spacing", -18 if _locale == "en-US" else -8)
	hero.add_child(pink)
	var lede := _label("One Publication IR produces TXT, Web,\nPrint, and EPUB. Presentation changes;\nmanuscript truth does not." if _locale == "en-US" else "一份 Publication IR 生成 TXT、Web、Print 与 EPUB。\n展示会变，稿件事实不会。", 16, 420, C.muted)
	lede.position = Vector2(18, 327 if _locale == "en-US" else 270)
	lede.size = Vector2(page_width - 36, 100)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_format_showcase(hero, Vector2(18, 405 if _locale == "en-US" else 350), Vector2(page_width - 36, 720), true)
	_build_format_strip(Vector2(page_x, 1275), Vector2(page_width, 320), true)
	_build_reading_preview(Vector2(page_x, 1615), Vector2(page_width, 220), true)

func _build_format_showcase(parent: Control, pos: Vector2, showcase_size: Vector2, phone: bool) -> void:
	var showcase := _panel(pos, showcase_size, Color("fffdfc"), 20, Color(0,0,0,0), 0)
	parent.add_child(showcase)
	var formats := ["TXT", "WEB", "PRINT", "EPUB"]
	var captions := ["Clean text", "Web", "Print", "EPUB"]
	var fills := [C.valid_soft, Color("eef8fb"), C.evidence_soft, C.editorial_soft]
	var cols := 2 if phone else 4
	var gap := 12.0
	var card_w := (showcase_size.x - gap * (cols - 1) - (20 if phone else 0)) / cols
	var card_h := 300.0 if phone else 250.0
	for i in range(formats.size()):
		var col := i % cols
		var row := i / cols
		var card := _panel(Vector2((10 if phone else 0) + col * (card_w + gap), row * (card_h + gap)), Vector2(card_w, card_h), fills[i], 18, Color("dbcfe2"), 1, Color(0.18,0.12,0.24,0.05), 4)
		if i == 3:
			var dark := _panel(Vector2.ZERO, Vector2(card_w, card_h), Color("fffdfc"), 18, Color("392f39"), 6)
			card = dark
		var tag := _pill(str(formats[i]), Vector2(10, -7), Vector2(54, 26), fills[i], C.muted, 9, 720)
		card.add_child(tag)
		var page := _panel(Vector2(12, 48), Vector2(card_w - 24, card_h - 98), Color("fffdfc"), 7, Color("ded5df"), 1)
		card.add_child(page)
		var heading := _label("Chapter 1 · Nightfall…", 9, 650, C.ink)
		heading.position = Vector2(8, 24)
		heading.size = Vector2(page.size.x - 16, 24)
		page.add_child(heading)
		for j in range(4):
			var line := ColorRect.new()
			line.color = Color(0.25,0.22,0.28,0.16)
			line.position = Vector2(10, 62 + j * 23)
			line.size = Vector2(max(page.size.x - 30 - j * 10, 20.0), 4)
			page.add_child(line)
		var cap := _label(str(captions[i]), 11, 520, C.muted)
		cap.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cap.position = Vector2(0, card_h - 34)
		cap.size = Vector2(card_w, 22)
		card.add_child(cap)
		showcase.add_child(card)

func _build_format_strip(pos: Vector2, strip_size: Vector2, phone: bool) -> void:
	var strip := _panel(pos, strip_size, Color("fffdfc"), 18, Color("e8ddea"), 1)
	_stage.add_child(strip)
	var formats := [["TXT", "Exact text, no presentation"], ["WEB", "Responsive reading surface"], ["PRINT", "Paged-media composition"], ["EPUB", "Reflowable ebook package"]]
	if phone:
		for i in range(formats.size()):
			var row := _panel(Vector2(14, 14 + i * 72), Vector2(strip_size.x - 28, 62), Color("fffdfc"), 12, Color("e7deea"), 1)
			var text := _label("%s   %s" % [formats[i][0], formats[i][1]], 12, 650, C.ink)
			text.position = Vector2(14, 19)
			text.size = Vector2(row.size.x - 28, 24)
			row.add_child(text)
			strip.add_child(row)
	else:
		var intro_w := 210.0
		var intro := _label("Publication\nworkbench", 15, 720, C.ink)
		intro.position = Vector2(20, 19)
		intro.size = Vector2(intro_w - 30, 50)
		strip.add_child(intro)
		var cell_w := (strip_size.x - intro_w) / 4.0
		for i in range(formats.size()):
			var cell := _panel(Vector2(intro_w + i * cell_w, 0), Vector2(cell_w, strip_size.y), Color("fffdfc"), 0, Color("e7deea"), 1)
			var text := _label("%s\n%s" % [formats[i][0], formats[i][1]], 12, 650, C.ink)
			text.position = Vector2(18, 28)
			text.size = Vector2(cell_w - 36, 60)
			cell.add_child(text)
			strip.add_child(cell)

func _build_reading_preview(pos: Vector2, preview_size: Vector2, phone: bool) -> void:
	var preview := _panel(pos, preview_size, Color("fffdfc"), 22, Color("e8ddea"), 1)
	_stage.add_child(preview)
	var heart := _mixed_label("♡", 17, 650, C.editorial)
	heart.position = Vector2(18, 18)
	heart.size = Vector2(24, 24)
	preview.add_child(heart)
	var label := _label("READING PREVIEW", 10, 760, C.muted)
	label.position = Vector2(344 if not phone else 60, 18)
	label.size = Vector2(180, 20)
	preview.add_child(label)
	var title := _label("EPUB", 16, 720, C.ink)
	title.position = Vector2(344 if not phone else 60, 42)
	title.size = Vector2(120, 24)
	preview.add_child(title)

func _draw() -> void:
	var route := _current_route()
	if not EDITORIAL_STAGE_HEIGHTS.has(route):
		super._draw()
		return
	draw_rect(Rect2(Vector2.ZERO, size), C.bg)
	if route == "/publication":
		draw_rect(Rect2(Vector2(23, 63), Vector2(max(size.x - 38, 0), max(size.y - 63, 0))), Color("fff8e9"))
		_soft_circle(Vector2(size.x * 0.18, 190), min(size.x * 0.24, 300.0), Color(0.95,0.55,0.72,0.035))
		_soft_circle(Vector2(size.x * 0.75, 560), min(size.x * 0.24, 320.0), Color(0.94,0.78,0.38,0.035))
	else:
		_soft_circle(Vector2(size.x * 0.14, 210), min(size.x * 0.22, 300.0), Color(0.94,0.75,0.35,0.025))
		_soft_circle(Vector2(size.x * 0.78, 520), min(size.x * 0.20, 280.0), Color(0.56,0.49,0.83,0.018))
	var stripe_colors := [C.project, C.runtime, C.editorial, C.evidence, C.valid]
	var stripe_x := 42.0 if _layout == "desktop" else 30.0
	for i in range(18):
		var col: Color = stripe_colors[i % stripe_colors.size()]
		col.a = 0.35
		draw_rect(Rect2(Vector2(stripe_x + i * 17.0, 63.0), Vector2(9.0, 4.0)), col)
