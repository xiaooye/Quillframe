extends "res://scripts/route_catalog.gd"

const SYSTEM_STAGE_HEIGHTS := {
	"/inspect": {"desktop": 1160.0, "compact": 1350.0, "phone": 1580.0},
	"/playground": {"desktop": 1320.0, "compact": 1480.0, "phone": 1680.0},
	"/agents": {"desktop": 1320.0, "compact": 1540.0, "phone": 1840.0},
}

func _build() -> void:
	var route := _current_route()
	if not SYSTEM_STAGE_HEIGHTS.has(route):
		super._build()
		return
	_build_system_route(route)

func _build_system_route(route: String) -> void:
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
	var heights: Dictionary = SYSTEM_STAGE_HEIGHTS[route]
	_stage.custom_minimum_size = Vector2(max(size.x, 320.0), float(heights[_layout]))
	_scroll.add_child(_stage)
	match route:
		"/inspect": _build_inspect_route()
		"/playground": _build_playground_route()
		"/agents": _build_agents_route()
	_build_header()
	_style_scrollbar()

func _build_inspect_route() -> void:
	if _layout == "phone":
		_build_inspect_phone()
	else:
		_build_inspect_desktop(_layout == "compact")

func _build_inspect_desktop(compact: bool) -> void:
	var page_x := 40.0 if compact else 70.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 110.0 if compact else 122.0
	var hero_h := 450.0 if compact else 416.0
	var hero := _route_hero_panel(Vector2(page_x, hero_y), Vector2(page_width, hero_h), 28)
	var pad := 48.0
	var eyebrow := _label("PROJECT INSPECTOR" if _locale == "en-US" else "项目检查器", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, pad + 1)
	eyebrow.size = Vector2(220, 22)
	hero.add_child(eyebrow)
	var title_text := "Resolve the\nproject before any\ntool touches it." if _locale == "en-US" else "任何工具动手之前，\n先把 Project 解析清楚。"
	var title := _label(title_text, 62 if _locale == "en-US" else 52, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, pad + 28)
	title.size = Vector2(610, 190)
	title.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -9)
	hero.add_child(title)
	var lede_text := "Inspect the manifest, exact Framework lock, attestation, and\nstructural evidence locally. Files are not uploaded and inspection\ngrants no new Project authority." if _locale == "en-US" else "在浏览器本地检查 manifest、精确 Framework lock、attestation 与结构证据。\n文件不会上传，inspection 也不会因此获得新的 Project authority。"
	var lede := _label(lede_text, 17, 420, C.muted)
	lede.position = Vector2(pad, 288 if _locale == "en-US" else 220)
	lede.size = Vector2(610, 105)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_manifest_stack(hero, Vector2(page_width * 0.57, 63), Vector2(page_width * 0.40, 280), false)
	_build_project_picker(Vector2(page_x, hero_y + hero_h + 32), Vector2(page_width, 390), false)

func _build_inspect_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero := _route_hero_panel(Vector2(page_x, 89), Vector2(page_width, 633), 22)
	var eyebrow := _label("PROJECT INSPECTOR" if _locale == "en-US" else "项目检查器", 11, 820, C.editorial)
	eyebrow.position = Vector2(18, 23)
	eyebrow.size = Vector2(220, 22)
	hero.add_child(eyebrow)
	var title_text := "Resolve the\nproject before\nany tool\ntouches it." if _locale == "en-US" else "任何工具动手\n之前，先把\nProject 解析清楚。"
	var title := _label(title_text, 39, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(18, 52)
	title.size = Vector2(page_width - 36, 190)
	title.add_theme_constant_override("line_spacing", -18 if _locale == "en-US" else -8)
	hero.add_child(title)
	var lede_text := "Inspect the manifest, exact Framework\nlock, attestation, and structural evidence\nlocally. Files are not uploaded and\ninspection grants no new Project authority." if _locale == "en-US" else "在浏览器本地检查 manifest、精确 Framework lock、\nattestation 与结构证据。文件不会上传，\ninspection 也不会因此获得新的 Project authority。"
	var lede := _label(lede_text, 16, 420, C.muted)
	lede.position = Vector2(18, 229 if _locale == "en-US" else 200)
	lede.size = Vector2(page_width - 36, 150)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_manifest_stack(hero, Vector2(36, 365 if _locale == "en-US" else 330), Vector2(page_width - 72, 250), true)
	_build_project_picker(Vector2(page_x, 742), Vector2(page_width, 470), true)

func _build_manifest_stack(parent: Control, pos: Vector2, stack_size: Vector2, phone: bool) -> void:
	var stack := _panel(pos, stack_size, Color("fffdfc"), 20, Color("eee5f0"), 1, Color(0.18,0.12,0.24,0.035), 4)
	parent.add_child(stack)
	for i in range(8):
		var line := ColorRect.new()
		line.color = Color(0.47,0.42,0.77,0.08)
		line.position = Vector2(0, 26 + i * 28)
		line.size = Vector2(stack_size.x, 1)
		stack.add_child(line)
	var local := _pill("LOCAL ONLY" if _locale == "en-US" else "仅本地", Vector2(-32 if not phone else 0, -14), Vector2(88, 30), C.valid_soft, Color("2f876d"), 10, 760, Color("b9dbce"))
	stack.add_child(local)
	var files := ["novelforge.toml", "novelforge.lock.json", "framework.attestation.json"]
	for i in range(files.size()):
		var row := _panel(Vector2(32 if not phone else 0, 30 + i * 59), Vector2(stack_size.x - (50 if not phone else 0), 50), Color("fffdfc"), 12, Color("e7deea"), 1, Color(0.18,0.12,0.24,0.045), 3)
		var icon := _label("▤", 14, 700, C.runtime)
		icon.position = Vector2(15, 14)
		icon.size = Vector2(22, 22)
		row.add_child(icon)
		var name := _label(str(files[i]), 13, 520, C.ink)
		name.position = Vector2(45, 13)
		name.size = Vector2(row.size.x - 55, 24)
		row.add_child(name)
		stack.add_child(row)
	var badge := _pill("✓ local only" if _locale == "en-US" else "✓ 仅本地", Vector2(stack_size.x - 101, stack_size.y - 44), Vector2(98, 32), C.valid_soft, Color("2f876d"), 12, 650, Color("b9dbce"))
	stack.add_child(badge)

func _build_project_picker(pos: Vector2, picker_size: Vector2, phone: bool) -> void:
	var picker := _panel(pos, picker_size, Color("fffdfc"), 25, Color("cbd7f1"), 1)
	_stage.add_child(picker)
	var tag := _panel(Vector2(24, 18), Vector2(112, 30), C.editorial_soft, 8, Color("efc8d9"), 1)
	var tag_text := _label("PROJECT FILES", 10, 760, C.editorial)
	tag_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tag_text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	tag_text.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	tag.add_child(tag_text)
	picker.add_child(tag)
	var icon_box := _panel(Vector2(picker_size.x / 2.0 - 30, 74), Vector2(60, 60), C.runtime_soft, 16, Color("cfc3ee"), 1, Color(0.18,0.12,0.24,0.05), 5)
	var house := _label("⌂", 28, 600, C.runtime)
	house.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	house.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	house.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	icon_box.add_child(house)
	picker.add_child(icon_box)
	var title := _label("Choose a NovelForge Project" if _locale == "en-US" else "选择 NovelForge Project", 30 if not phone else 25, 740, C.ink)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(20, 150)
	title.size = Vector2(picker_size.x - 40, 46)
	picker.add_child(title)
	var body := _label("The inspector detects novelforge.toml, the framework lock, optional attestation, core\nlogical directories, and quality evidence surfaces." if _locale == "en-US" else "检查器会识别 novelforge.toml、Framework lock、可选 attestation、\n核心逻辑目录和质量证据面。", 14, 420, C.muted)
	body.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	body.position = Vector2(30, 210)
	body.size = Vector2(picker_size.x - 60, 70)
	body.add_theme_constant_override("line_spacing", 4)
	picker.add_child(body)
	var button_w := 208.0
	var choose := _text_button("Choose project folder" if _locale == "en-US" else "选择 Project 文件夹", Vector2(picker_size.x / 2.0 - button_w - 6, 294), Vector2(button_w, 46), Color("80b7ec"), Color.WHITE, 15, 600, 8)
	picker.add_child(choose)
	var demo := _mixed_text_button("✦ Load demo project" if _locale == "en-US" else "✦ 加载演示 Project", Vector2(picker_size.x / 2.0 + 6, 294), Vector2(205, 46), C.runtime_soft, C.runtime, 15, 600, 8)
	picker.add_child(demo)
	if phone:
		choose.position = Vector2(28, 308)
		choose.size.x = picker_size.x - 56
		demo.position = Vector2(28, 364)
		demo.size.x = picker_size.x - 56

func _build_playground_route() -> void:
	if _layout == "phone":
		_build_playground_phone()
	else:
		_build_playground_desktop(_layout == "compact")

func _build_playground_desktop(compact: bool) -> void:
	var page_x := 40.0 if compact else 70.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 110.0 if compact else 122.0
	var hero_h := 550.0 if compact else 515.0
	var hero := _route_hero_panel(Vector2(page_x, hero_y), Vector2(page_width, hero_h), 28)
	var pad := 48.0
	var eyebrow := _label("LOCAL PLAYGROUND" if _locale == "en-US" else "本地 PLAYGROUND", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, pad + 1)
	eyebrow.size = Vector2(220, 22)
	hero.add_child(eyebrow)
	var title_text := "Make the\nexecution path\na deterministic\nthing you can\nplay with." if _locale == "en-US" else "把执行路径变成\n可以亲手试的\n确定性对象。"
	var title := _label(title_text, 62 if _locale == "en-US" else 52, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, pad + 28)
	title.size = Vector2(590, 320)
	title.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -9)
	hero.add_child(title)
	var lede_text := "Paste working text, choose a task mode, and inspect a browser-local\ntrace. No model call and no Project-state write." if _locale == "en-US" else "粘贴工作文本，选择 task mode，然后检查浏览器本地 trace。\n不会调用模型，也不会写入 Project state。"
	var lede := _label(lede_text, 17, 420, C.muted)
	lede.position = Vector2(pad, 410 if _locale == "en-US" else 310)
	lede.size = Vector2(590, 75)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_trace_preview(hero, Vector2(page_width * 0.59, 50), Vector2(page_width * 0.38, 405), false)
	_build_execution_board(Vector2(page_x, hero_y + hero_h + 32), Vector2(page_width, 520), false)

func _build_playground_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero := _route_hero_panel(Vector2(page_x, 89), Vector2(page_width, 729), 22)
	var eyebrow := _label("LOCAL PLAYGROUND" if _locale == "en-US" else "本地 PLAYGROUND", 11, 820, C.editorial)
	eyebrow.position = Vector2(18, 23)
	eyebrow.size = Vector2(220, 22)
	hero.add_child(eyebrow)
	var title_text := "Make the\nexecution path\na deterministic\nthing you can\nplay with." if _locale == "en-US" else "把执行路径\n变成可以亲手试的\n确定性对象。"
	var title := _label(title_text, 39, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(18, 52)
	title.size = Vector2(page_width - 36, 210)
	title.add_theme_constant_override("line_spacing", -18 if _locale == "en-US" else -8)
	hero.add_child(title)
	var lede_text := "Paste working text, choose a task mode,\nand inspect a browser-local trace. No\nmodel call and no Project-state write." if _locale == "en-US" else "粘贴工作文本，选择 task mode，然后检查浏览器本地 trace。\n不会调用模型，也不会写入 Project state。"
	var lede := _label(lede_text, 16, 420, C.muted)
	lede.position = Vector2(18, 270 if _locale == "en-US" else 225)
	lede.size = Vector2(page_width - 36, 120)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_trace_preview(hero, Vector2(36, 365 if _locale == "en-US" else 325), Vector2(page_width - 72, 350), true)
	_build_execution_board(Vector2(page_x, 838), Vector2(page_width, 650), true)

func _build_trace_preview(parent: Control, pos: Vector2, preview_size: Vector2, phone: bool) -> void:
	var canvas := _panel(pos, preview_size, Color("fffdf9"), 20, Color(0,0,0,0), 0)
	parent.add_child(canvas)
	for x in range(10, int(preview_size.x), 20):
		for y in range(10, int(preview_size.y), 20):
			var dot := ColorRect.new()
			dot.color = Color(0.84,0.65,0.35,0.22)
			dot.position = Vector2(x, y)
			dot.size = Vector2(2, 2)
			canvas.add_child(dot)
	var inner := _panel(Vector2(56 if not phone else 18, 92 if not phone else 12), Vector2(preview_size.x - (112 if not phone else 36), 230 if not phone else 308), Color("fffdfc"), 16, Color("decbbd"), 1, Color(0.18,0.12,0.24,0.05), 4)
	canvas.add_child(inner)
	var stages := ["DRAFT", "Context", "Evidence", "Result"]
	var fills := [C.evidence_soft, C.editorial_soft, C.evidence_soft, C.valid_soft]
	if phone:
		for i in range(stages.size()):
			var row := _panel(Vector2(18, 18 + i * 78), Vector2(inner.size.x - 36, 38), fills[i], 10, Color("e7deea"), 1)
			var text := _label(str(stages[i]), 13, 650 if i == 3 else 520, C.ink)
			text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			text.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
			row.add_child(text)
			inner.add_child(row)
			if i < stages.size() - 1:
				var arrow := _label("↓", 18, 600, C.muted)
				arrow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
				arrow.position = Vector2(0, 56 + i * 78)
				arrow.size = Vector2(inner.size.x, 24)
				inner.add_child(arrow)
	else:
		var gap := 12.0
		var stage_w := (inner.size.x - 54 - gap * 3) / 4.0
		for i in range(stages.size()):
			var row := _panel(Vector2(18 + i * (stage_w + gap), 96), Vector2(stage_w, 38), fills[i], 10, Color("e7deea"), 1)
			var text := _label(str(stages[i]), 12, 650 if i == 3 else 520, C.ink)
			text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			text.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
			row.add_child(text)
			inner.add_child(row)
	var note := _mixed_label("✦ deterministic preview", 10, 650, Color("92734a"))
	note.position = Vector2(preview_size.x - 158, preview_size.y - 30)
	note.size = Vector2(150, 20)
	canvas.add_child(note)

func _build_execution_board(pos: Vector2, board_size: Vector2, phone: bool) -> void:
	var board := _panel(pos, board_size, Color("fffdfc"), 25, Color("d9d0ec"), 1)
	_stage.add_child(board)
	var tag := _pill("✦ EXECUTION TRACE", Vector2(28, 24), Vector2(150, 30), Color("fffdfc"), C.runtime, 10, 720, Color("cfc3ee"))
	board.add_child(tag)
	var title := _label("DRAFT", 18, 760, C.ink)
	title.position = Vector2(28, 65)
	title.size = Vector2(180, 30)
	board.add_child(title)
	var modes := ["DRAFT", "REVISE", "AUDIT", "PLAN-CHAPTER"]
	for i in range(modes.size()):
		var b := _pill(str(modes[i]), Vector2(28 + (i % 3) * 88, 112 + (i / 3) * 44), Vector2(82 if i < 3 else 112, 34), C.runtime_soft if i == 0 else Color("fffdfc"), C.runtime if i == 0 else C.muted, 10, 650, Color("d8d0e8"))
		board.add_child(b)
	var trace := _panel(Vector2(320 if not phone else 28, 24 if not phone else 225), Vector2(board_size.x - (350 if not phone else 56), board_size.y - (48 if not phone else 255)), Color("fffdfc"), 18, Color("eee5f0"), 1)
	board.add_child(trace)
	var trace_text := _label("Context → Evidence → Result\n\nBrowser-local deterministic mock\nNo model call · no Project write", 14, 520, C.muted)
	trace_text.position = Vector2(24, 28)
	trace_text.size = Vector2(trace.size.x - 48, 140)
	trace_text.add_theme_constant_override("line_spacing", 8)
	trace.add_child(trace_text)

func _build_agents_route() -> void:
	if _layout == "phone":
		_build_agents_phone()
	else:
		_build_agents_desktop(_layout == "compact")

func _build_agents_desktop(compact: bool) -> void:
	var page_x := 40.0 if compact else 70.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 110.0 if compact else 122.0
	var hero_h := 560.0 if compact else 515.0
	var hero := _route_hero_panel(Vector2(page_x, hero_y), Vector2(page_width, hero_h), 28)
	var pad := 48.0
	var eyebrow := _label("AGENT SKILL · HOST BRIDGE V1", 11, 820, C.editorial)
	eyebrow.position = Vector2(pad, pad + 1)
	eyebrow.size = Vector2(280, 22)
	hero.add_child(eyebrow)
	hero.add_child(_pill("authority=false", Vector2(pad, pad + 26), Vector2(112, 28), Color("fffdfc"), C.ink, 12, 520, Color("e2dae7")))
	var title_text := "Let your agent\nuse NovelForge\nwithout bypassing\nNovelForge." if _locale == "en-US" else "让 Agent 使用\nNovelForge，\n但不能绕过\nNovelForge。"
	var title := _label(title_text, 62 if _locale == "en-US" else 52, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, pad + 67)
	title.size = Vector2(610, 280)
	title.add_theme_constant_override("line_spacing", -25 if _locale == "en-US" else -9)
	hero.add_child(title)
	var lede_text := "The portable Agent Skill uses the public Host Bridge to discover\ncapabilities and inspect Project, Context, and semantic contracts\nwhile writes remain Core-owned." if _locale == "en-US" else "便携 Agent Skill 通过公开 Host Bridge 发现能力并检查 Project、Context 与语义契约；\n写入权限仍由 Core 持有。"
	var lede := _label(lede_text, 17, 420, C.muted)
	lede.position = Vector2(pad, 385 if _locale == "en-US" else 330)
	lede.size = Vector2(610, 105)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_agent_patch_bay(hero, Vector2(page_width * 0.57, 125), Vector2(page_width * 0.39, 267), false)
	var sig := _label("Host Bridge · authority=false", 10, 600, C.muted)
	sig.position = Vector2(page_width - 230, hero_h - 70)
	sig.size = Vector2(190, 20)
	hero.add_child(sig)
	_build_agent_recipe(Vector2(page_x, hero_y + hero_h + 32), Vector2(page_width, 520), false)

func _build_agents_phone() -> void:
	var page_x := 16.0
	var page_width := size.x - 32.0
	var hero := _route_hero_panel(Vector2(page_x, 89), Vector2(page_width, 1040), 22)
	var eyebrow := _label("AGENT SKILL · HOST BRIDGE V1", 11, 820, C.editorial)
	eyebrow.position = Vector2(18, 23)
	eyebrow.size = Vector2(280, 22)
	hero.add_child(eyebrow)
	hero.add_child(_pill("authority=false", Vector2(18, 50), Vector2(112, 28), Color("fffdfc"), C.ink, 12, 520, Color("e2dae7")))
	var title_text := "Let your\nagent use\nNovelForge\nwithout\nbypassing\nNovelForge." if _locale == "en-US" else "让 Agent 使用\nNovelForge，\n但不能绕过\nNovelForge。"
	var title := _label(title_text, 39, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(18, 88)
	title.size = Vector2(page_width - 36, 260)
	title.add_theme_constant_override("line_spacing", -18 if _locale == "en-US" else -8)
	hero.add_child(title)
	var lede_text := "The portable Agent Skill uses the public\nHost Bridge to discover capabilities and\ninspect Project, Context, and semantic\ncontracts while writes remain Core-owned." if _locale == "en-US" else "便携 Agent Skill 通过公开 Host Bridge 发现能力，\n并检查 Project、Context 与语义契约；\n写入权限仍由 Core 持有。"
	var lede := _label(lede_text, 16, 420, C.muted)
	lede.position = Vector2(18, 365 if _locale == "en-US" else 300)
	lede.size = Vector2(page_width - 36, 145)
	lede.add_theme_constant_override("line_spacing", 4)
	hero.add_child(lede)
	_build_agent_patch_bay(hero, Vector2(36, 478 if _locale == "en-US" else 420), Vector2(page_width - 72, 500), true)
	_build_agent_recipe(Vector2(page_x, 1155), Vector2(page_width, 560), true)

func _build_agent_patch_bay(parent: Control, pos: Vector2, bay_size: Vector2, phone: bool) -> void:
	var bay := _panel(pos, bay_size, Color("fffdfc"), 18, Color("cfc3ee"), 1, Color(0.18,0.12,0.24,0.05), 5)
	parent.add_child(bay)
	var label := _label("AGENT PATCH BAY", 10, 760, C.runtime)
	label.position = Vector2(18, 16)
	label.size = Vector2(180, 20)
	bay.add_child(label)
	var agents := ["Claude Code", "Codex", "Cursor", "OpenCode", "Custom agent"]
	var cols := 1 if phone else 2
	var gap := 8.0
	var cell_w := bay_size.x - 36 if phone else (bay_size.x - 44) / 2.0
	var cell_h := 56.0
	for i in range(agents.size()):
		var col := i % cols
		var row := i / cols
		var cell := _panel(Vector2(18 + col * (cell_w + gap), 44 + row * (cell_h + gap)), Vector2(cell_w, cell_h), Color("fbf9fc"), 10, Color("e5dcea"), 1)
		if str(agents[i]) == "Codex":
			cell.add_theme_stylebox_override("panel", _button_box(Color("fffdfc"), 10))
		var icon_box := _panel(Vector2(12, 12), Vector2(32, 32), C.runtime_soft, 10)
		var letter := _label("O" if str(agents[i]) == "OpenCode" else "C", 16, 760, C.runtime)
		letter.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		letter.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		letter.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		icon_box.add_child(letter)
		cell.add_child(icon_box)
		var name := _label(str(agents[i]), 13, 650, C.ink)
		name.position = Vector2(54, 16)
		name.size = Vector2(cell_w - 64, 24)
		cell.add_child(name)
		bay.add_child(cell)
	var footer := _label("Host Bridge · authority=false", 9, 600, C.muted)
	footer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	footer.position = Vector2(18, bay_size.y - 30)
	footer.size = Vector2(bay_size.x - 36, 20)
	bay.add_child(footer)

func _build_agent_recipe(pos: Vector2, recipe_size: Vector2, phone: bool) -> void:
	var panel := _route_hero_panel(pos, recipe_size, 24)
	var eyebrow := _label("HOST RECIPE", 10, 760, C.muted)
	eyebrow.position = Vector2(28, 28)
	eyebrow.size = Vector2(150, 20)
	panel.add_child(eyebrow)
	var title := _label("Codex uses the same public boundary." if _locale == "en-US" else "Codex 使用同一条公开边界。", 30 if not phone else 25, 740, C.ink)
	title.position = Vector2(28, 55)
	title.size = Vector2(recipe_size.x - 56, 48)
	panel.add_child(title)
	var left := _panel(Vector2(28, 122), Vector2(recipe_size.x * (0.36 if not phone else 1.0) - (42 if not phone else 56), 310), Color("fffdfc"), 16, Color("ded5ea"), 1)
	panel.add_child(left)
	var left_title := _label("Match capabilities\nwithout inventing authority", 25, 740, C.ink)
	left_title.position = Vector2(18, 50)
	left_title.size = Vector2(left.size.x - 36, 90)
	left_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	left.add_child(left_title)
	if not phone:
		var right := _panel(Vector2(recipe_size.x * 0.39, 122), Vector2(recipe_size.x * 0.58, 310), Color("fffdfc"), 16, Color("ded5ea"), 1)
		panel.add_child(right)
		var instruction := _label("HOST INSTRUCTION\n\n1. Read agent-skills/novelforge/SKILL.md\n2. Discover capabilities\n3. Inspect before proposing writes\n4. Leave Core-owned writes to Core", 13, 520, C.muted)
		instruction.position = Vector2(20, 18)
		instruction.size = Vector2(right.size.x - 40, 230)
		instruction.add_theme_constant_override("line_spacing", 7)
		right.add_child(instruction)

func _draw() -> void:
	var route := _current_route()
	if not SYSTEM_STAGE_HEIGHTS.has(route):
		super._draw()
		return
	draw_rect(Rect2(Vector2.ZERO, size), C.bg)
	_soft_circle(Vector2(size.x * 0.72, 230), min(size.x * 0.25, 350.0), Color(0.95,0.76,0.86,0.022))
	_soft_circle(Vector2(size.x * 0.43, 580), min(size.x * 0.22, 300.0), Color(0.56,0.49,0.83,0.016))
	var stripe_colors := [C.project, C.runtime, C.editorial, C.evidence, C.valid]
	var stripe_x := 42.0 if _layout == "desktop" else 30.0
	for i in range(18):
		var col: Color = stripe_colors[i % stripe_colors.size()]
		col.a = 0.35
		draw_rect(Rect2(Vector2(stripe_x + i * 17.0, 63.0), Vector2(9.0, 4.0)), col)
