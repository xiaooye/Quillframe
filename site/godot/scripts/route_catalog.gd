extends "res://scripts/route_surfaces.gd"

const ROUTE_STAGE_HEIGHTS := {
	"/studio": {"desktop": 1180.0, "compact": 1400.0, "phone": 1700.0},
	"/changelog": {"desktop": 1020.0, "compact": 1160.0, "phone": 1480.0},
}

func _build() -> void:
	var route := _current_route()
	if not ROUTE_STAGE_HEIGHTS.has(route):
		super._build()
		return
	_build_catalog_route(route)

func _build_catalog_route(route: String) -> void:
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
	var heights: Dictionary = ROUTE_STAGE_HEIGHTS[route]
	_stage.custom_minimum_size = Vector2(max(size.x, 320.0), float(heights[_layout]))
	_scroll.add_child(_stage)
	match route:
		"/studio": _build_studio_route()
		"/changelog": _build_changelog_route()
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
			if route == "/studio" and button.text == "Studio":
				button.add_theme_color_override("font_color", C.runtime)
				button.add_theme_color_override("font_hover_color", C.runtime)
				button.add_theme_stylebox_override("normal", _button_box(C.runtime_soft, 10))

func _build_studio_route() -> void:
	if _layout == "phone":
		_build_studio_phone()
	else:
		_build_studio_desktop(_layout == "compact")

func _build_studio_desktop(compact: bool) -> void:
	var page_x := 40.0 if compact else 70.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 110.0 if compact else 122.0
	var hero_h := 770.0 if compact else 738.0
	var hero := _route_hero_panel(Vector2(page_x, hero_y), Vector2(page_width, hero_h), 28)
	var pad := 40.0 if compact else 48.0
	var eyebrow := _label("NOVELFORGE STUDIO" if _locale == "en-US" else "NOVELFORGE STUDIO", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, pad + 1)
	eyebrow.size = Vector2(260, 22)
	hero.add_child(eyebrow)
	var title_text := "The creative\nworkbench\naround Core —\nwith progressive\ndisclosure instead\nof dashboard\noverload." if _locale == "en-US" else "把创作放在前台，\n把运行证据留在\n需要时展开。"
	var title := _label(title_text, 62 if _locale == "en-US" else 54, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, pad + 26)
	title.size = Vector2(590, 450)
	title.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -10)
	hero.add_child(title)
	var lede_text := "Phase 2C now ships a real read-only SolidJS shell: bilingual, mobile-\nfirst, loopback-hosted, no default polling, and backed by the public\nHost Bridge. Local Web remains first-class; Tauri is still optional." if _locale == "en-US" else "第二阶段 C 已有真实的只读 SolidJS 应用壳：双语、移动优先、无默认轮询，\n通过本地回环宿主桥接层读取 Core 的公开能力；本地网页端是一等产品入口，\nTauri 仍是可选宿主。"
	var lede := _label(lede_text, 17, 420, C.muted)
	lede.position = Vector2(pad, 535 if _locale == "en-US" else 440)
	lede.size = Vector2(610, 108)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	var cta_y := 646.0 if _locale == "en-US" else 555.0
	var cta := _mixed_text_button("✦ Open Hosted Studio" if _locale == "en-US" else "✦ 打开 Hosted Studio", Vector2(pad, cta_y), Vector2(192, 44), C.runtime, Color.WHITE, 14, 600, 8)
	cta.pressed.connect(_open_external.bind(STUDIO_URL))
	hero.add_child(cta)
	var visual_x := page_width * 0.56
	var visual_w := page_width - visual_x - pad
	_build_studio_terminal(hero, Vector2(visual_x, 257), Vector2(visual_w, 227))
	var signature := _mixed_label("✦ Studio ♡", 11, 650, Color("efc5dc"))
	signature.position = Vector2(page_width - 140, hero_h - 70)
	signature.size = Vector2(100, 22)
	hero.add_child(signature)
	_build_studio_cards(Vector2(page_x, hero_y + hero_h + 32), page_width, false)

func _build_studio_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero := _route_hero_panel(Vector2(page_x, 89), Vector2(page_width, 1090), 22)
	var pad := 18.0
	var eyebrow := _label("NOVELFORGE STUDIO", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, 23)
	eyebrow.size = Vector2(220, 22)
	hero.add_child(eyebrow)
	var title_text := "The creative\nworkbench\naround Core —\nwith\nprogressive\ndisclosure\ninstead of\ndashboard\noverload." if _locale == "en-US" else "把创作放在\n前台，把运行\n证据留在需要\n时展开。"
	var title := _label(title_text, 39, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, 51)
	title.size = Vector2(page_width - 36, 390)
	title.add_theme_constant_override("line_spacing", -18 if _locale == "en-US" else -8)
	hero.add_child(title)
	var lede_text := "Phase 2C now ships a real read-only\nSolidJS shell: bilingual, mobile-first,\nloopback-hosted, no default polling,\nand backed by the public Host Bridge.\nLocal Web remains first-class; Tauri is\nstill optional." if _locale == "en-US" else "第二阶段 C 已有真实的只读 SolidJS 应用壳：\n双语、移动优先、无默认轮询，通过本地回环\n宿主桥接层读取 Core 的公开能力；本地网页端\n是一等产品入口，Tauri 仍是可选宿主。"
	var lede := _label(lede_text, 16, 420, C.muted)
	lede.position = Vector2(pad, 433 if _locale == "en-US" else 300)
	lede.size = Vector2(page_width - 36, 190)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	var cta_y := 592.0 if _locale == "en-US" else 440.0
	var cta := _mixed_text_button("✦ Open Hosted Studio" if _locale == "en-US" else "✦ 打开 Hosted Studio", Vector2(pad, cta_y), Vector2(192, 44), C.runtime, Color.WHITE, 14, 600, 8)
	cta.pressed.connect(_open_external.bind(STUDIO_URL))
	hero.add_child(cta)
	var visual_y := 660.0 if _locale == "en-US" else 520.0
	_build_studio_terminal(hero, Vector2(pad + 17, visual_y), Vector2(page_width - 70, 250))
	_build_studio_cards(Vector2(page_x, 1210), page_width, true)

func _build_studio_terminal(parent: Control, pos: Vector2, terminal_size: Vector2) -> void:
	var terminal := _panel(pos, terminal_size, Color("fffdfd"), 15, Color("cfc0e7"), 1, Color(0.25,0.16,0.32,0.08), 8)
	parent.add_child(terminal)
	var bar := _panel(Vector2.ZERO, Vector2(terminal_size.x, 42), Color("fbf0f7"), 15)
	terminal.add_child(bar)
	for i in range(3):
		var dot := ColorRect.new()
		dot.color = [Color("d983af"), Color("e0bd65"), Color("6fc898")][i]
		dot.position = Vector2(12 + i * 15, 18)
		dot.size = Vector2(8, 8)
		bar.add_child(dot)
	var host := _label("studio.novelforge.wei-dev.com", 11, 650, Color("d9cae6"))
	host.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	host.position = Vector2(70, 11)
	host.size = Vector2(terminal_size.x - 90, 20)
	bar.add_child(host)
	var lines := _label("host: cloudflare\ncore: unbound\nauthority: false\nmode: read-only", 13, 520, Color("b5e6ca"))
	lines.position = Vector2(28, 72)
	lines.size = Vector2(terminal_size.x - 50, 120)
	lines.add_theme_constant_override("line_spacing", 8)
	terminal.add_child(lines)

func _build_studio_cards(pos: Vector2, width: float, phone: bool) -> void:
	var cards := [
		["Run / Context Inspector", "Shows the crucial distinction between semantic support and evidence that really entered model context."],
		["Project Hub / Scene", "A safe read projection for project identity and a creator/inspector scene workspace prototype."],
		["Portable Host Bridge", "Allowlisted read operations shared by CLI, Local Web/app, hosted UI, and Agent Skill consumers."],
		["Real SolidJS product shell", "Current baseline shell, responsive surfaces, deterministic CI, and fingerprint-bound visual QA."],
	]
	_build_route_cards(pos, width, cards, phone)

func _build_changelog_route() -> void:
	if _layout == "phone":
		_build_changelog_phone()
	else:
		_build_changelog_desktop(_layout == "compact")

func _build_changelog_desktop(compact: bool) -> void:
	var page_x := 40.0 if compact else 70.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 110.0 if compact else 122.0
	var hero_h := 520.0 if compact else 483.0
	var hero := _route_hero_panel(Vector2(page_x, hero_y), Vector2(page_width, hero_h), 28)
	var pad := 48.0
	var eyebrow := _label("RELEASE TRUTH" if _locale == "en-US" else "版本状态", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, pad + 1)
	eyebrow.size = Vector2(220, 22)
	hero.add_child(eyebrow)
	var title_text := "A changelog\nthat separates\nimplementation\nfrom aspiration." if _locale == "en-US" else "版本记录只写\n已经发生的事。"
	var title := _label(title_text, 62 if _locale == "en-US" else 54, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, pad + 28)
	title.size = Vector2(580, 250)
	title.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -10)
	hero.add_child(title)
	var lede_text := "NovelForge is pre-1.0. The current ledger records merged\nmachine/product behavior and keeps remaining Core/Product gaps\nexplicit rather than silently promoting roadmaps into capabilities." if _locale == "en-US" else "NovelForge 仍处于 1.0 之前。当前记录只描述已经合入的机器契约与产品行为，\n并把剩余缺口明确留在开发计划里，不把路线图提前包装成能力。"
	var lede := _label(lede_text, 17, 420, C.muted)
	lede.position = Vector2(pad, 350 if _locale == "en-US" else 255)
	lede.size = Vector2(610, 110)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_release_oval(hero, Vector2(page_width * 0.63, 152), Vector2(320, 180))
	var cards := [
		["0.8.0 identity", "Manifest, CLI, Skill, Project SDK default, MCP metadata, and documentation governance use one pre-1.0 development identity."],
		["Breaking cleanup is still possible", "Before 1.0, justified machine-contract cleanup may land on latest main when architecture and deterministic CI support it."],
		["History stays history", "Older 7.x changelog/spec records retain their original meaning; active docs do not rewrite the past to make current naming look inevitable."],
	]
	_build_route_cards(Vector2(page_x, hero_y + hero_h + 32), page_width, cards, false)

func _build_changelog_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero := _route_hero_panel(Vector2(page_x, 89), Vector2(page_width, 668), 22)
	var eyebrow := _label("RELEASE TRUTH" if _locale == "en-US" else "版本状态", 11, 820, C.editorial)
	eyebrow.position = Vector2(18, 23)
	eyebrow.size = Vector2(220, 22)
	hero.add_child(eyebrow)
	var title_text := "A changelog\nthat separates\nimplementation\nfrom\naspiration." if _locale == "en-US" else "版本记录只写\n已经发生的事。"
	var title := _label(title_text, 39, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(18, 52)
	title.size = Vector2(page_width - 36, 230)
	title.add_theme_constant_override("line_spacing", -18 if _locale == "en-US" else -8)
	hero.add_child(title)
	var lede_text := "NovelForge is pre-1.0. The current ledger\nrecords merged machine/product behavior\nand keeps remaining Core/Product gaps\nexplicit rather than silently promoting\nroadmaps into capabilities." if _locale == "en-US" else "NovelForge 仍处于 1.0 之前。当前记录只描述\n已经合入的机器契约与产品行为，并把剩余缺口\n明确留在开发计划里，不把路线图提前包装成能力。"
	var lede := _label(lede_text, 16, 420, C.muted)
	lede.position = Vector2(18, 270 if _locale == "en-US" else 180)
	lede.size = Vector2(page_width - 36, 180)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_release_oval(hero, Vector2(45, 438 if _locale == "en-US" else 350), Vector2(page_width - 90, 180))
	var cards := [
		["0.8.0 identity", "Manifest, CLI, Skill, Project SDK default, MCP metadata, and documentation governance use one pre-1.0 development identity."],
		["Breaking cleanup is still possible", "Before 1.0, justified machine-contract cleanup may land on latest main when architecture and deterministic CI support it."],
		["History stays history", "Older 7.x changelog/spec records retain their original meaning; active docs do not rewrite the past to make current naming look inevitable."],
	]
	_build_route_cards(Vector2(page_x, 777), page_width, cards, true)

func _build_release_oval(parent: Control, pos: Vector2, oval_size: Vector2) -> void:
	var oval := _panel(pos, oval_size, Color("f7fbf8"), int(oval_size.y / 2.0), Color("c8d9d0"), 1, Color(0.18,0.12,0.24,0.06), 8)
	parent.add_child(oval)
	var version := _label("0.8.x", 60, 780, C.ink)
	version.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	version.position = Vector2(0, 43)
	version.size = Vector2(oval_size.x, 78)
	oval.add_child(version)
	var meta := _label("current main", 11, 520, C.muted)
	meta.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	meta.position = Vector2(0, 128)
	meta.size = Vector2(oval_size.x, 22)
	oval.add_child(meta)

func _route_hero_panel(pos: Vector2, hero_size: Vector2, radius: int) -> Panel:
	var hero := _panel(pos, hero_size, Color("fffdfc"), radius, Color("e8ddea"), 1, Color(0.18,0.12,0.24,0.09), 12)
	_stage.add_child(hero)
	var inset := 8.0 if radius >= 28 else 6.0
	var inner := _panel(Vector2(inset, inset), hero_size - Vector2(inset * 2.0, inset * 2.0), Color(0,0,0,0), radius - 8, Color(0.95,0.74,0.84,0.30), 1)
	inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hero.add_child(inner)
	return hero

func _build_route_cards(pos: Vector2, width: float, cards: Array, phone: bool) -> void:
	if phone:
		var y := pos.y
		for i in range(cards.size()):
			_stage.add_child(_catalog_card(Vector2(pos.x, y), Vector2(width, 190), i, str(cards[i][0]), str(cards[i][1])))
			y += 204.0
	else:
		var gap := 12.0
		var card_w := (width - gap * 2.0) / 3.0
		for i in range(cards.size()):
			var row := i / 3
			var col := i % 3
			_stage.add_child(_catalog_card(Vector2(pos.x + col * (card_w + gap), pos.y + row * 204.0), Vector2(card_w, 190), i, str(cards[i][0]), str(cards[i][1])))

func _catalog_card(pos: Vector2, card_size: Vector2, index: int, title_text: String, body_text: String) -> Panel:
	var fills := [Color("fff7fa"), Color("faf8ff"), Color("f8fcfa"), Color("fffaf0")]
	var card := _panel(pos, card_size, fills[index % fills.size()], 20, Color("e8ddea"), 1)
	var idx := _label("%02d" % (index + 1), 9, 760, C.muted)
	idx.position = Vector2(20, 20)
	idx.size = Vector2(44, 20)
	card.add_child(idx)
	var title := _label(title_text, 19, 740, C.ink)
	title.position = Vector2(20, 50)
	title.size = Vector2(card_size.x - 40, 48)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(title)
	var body := _label(body_text, 12, 430, C.muted)
	body.position = Vector2(20, 101)
	body.size = Vector2(card_size.x - 40, 74)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_theme_constant_override("line_spacing", 4)
	card.add_child(body)
	return card

func _draw() -> void:
	var route := _current_route()
	if not ROUTE_STAGE_HEIGHTS.has(route):
		super._draw()
		return
	draw_rect(Rect2(Vector2.ZERO, size), C.bg)
	_soft_circle(Vector2(size.x * 0.72, 230), min(size.x * 0.25, 350.0), Color(0.95,0.76,0.86,0.025))
	_soft_circle(Vector2(size.x * 0.45, 520), min(size.x * 0.20, 280.0), Color(0.56,0.49,0.83,0.018))
	var stripe_colors := [C.project, C.runtime, C.editorial, C.evidence, C.valid]
	var stripe_x := 42.0 if _layout == "desktop" else 30.0
	for i in range(18):
		var col: Color = stripe_colors[i % stripe_colors.size()]
		col.a = 0.35
		draw_rect(Rect2(Vector2(stripe_x + i * 17.0, 63.0), Vector2(9.0, 4.0)), col)
