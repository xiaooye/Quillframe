extends "res://scripts/interaction_parity.gd"

# Final visual-completion layer. The earlier parity stack proved routing,
# renderer, interaction and first-viewport geometry; this layer owns the
# remaining product-surface completeness contract: full Home body sections,
# CJK-safe localized controls, Architecture body detail, and an actually
# rendered Publication preview/provenance workbench.

var _home_capability_index := 0
var _home_budget := 3
var _home_gates := [true, true, false, true]
var _publication_profile := 3
var _architecture_selected := 0
var _architecture_run_step := -1

func _build() -> void:
	super._build()
	_repair_localized_control_fonts(self)
	var route := _current_route()
	match route:
		"/":
			if _stage != null:
				_stage.custom_minimum_size.y = 4300.0 if _layout == "phone" else 3150.0
			_set_dataset("novelforgeHomeSections", "complete")
		"/architecture":
			_patch_architecture_copy_geometry()
			_append_architecture_inspector()
			_set_dataset("novelforgeArchitectureInspector", "ready")
		"/publication":
			if _stage != null:
				_stage.custom_minimum_size.y = 2780.0 if _layout == "phone" else 1660.0
			_set_dataset("novelforgePublicationPreview", "ready")
	_set_dataset("novelforgeTypographyCjk", "ready")
	_set_dataset("novelforgeVisualCompletion", "ready")

func _repair_localized_control_fonts(node: Node) -> void:
	for child in node.get_children():
		if child is Button:
			var button := child as Button
			if _contains_cjk(button.text) or _contains_extended_glyph(button.text):
				button.add_theme_font_override("font", _mixed_font(650))
		elif child is Label:
			var label := child as Label
			if _contains_cjk(label.text) and label.text.begins_with("⌕"):
				label.add_theme_font_override("font", _mixed_font(430))
		_repair_localized_control_fonts(child)

func _contains_extended_glyph(text: String) -> bool:
	for i in range(text.length()):
		if text.unicode_at(i) > 0x7f:
			return true
	return false

# -----------------------------------------------------------------------------
# Home: restore the sections that exist in the golden product fixture instead
# of stopping after a three-card placeholder row.
# -----------------------------------------------------------------------------

func _home_capabilities() -> Array:
	if _locale == "zh-CN":
		return [
			{"icon":"🫧", "eyebrow":"上下文", "title":"被判定有帮助 ≠ 真正进入上下文", "body":"运行收据区分可用支持材料、真正进入受预算约束上下文包的证据，以及因为预算、可见性或故事时间被排除的证据。", "meta":"novelforge_run_receipt_v1"},
			{"icon":"✓", "eyebrow":"就绪状态", "title":"所有必要审查绑定同一份候选稿", "body":"文本表面、读者参与、连续性与独立语义证据只要缺失、等待或失败，候选稿就不会被标记为可进入用户审查。", "meta":"novelforge_production_readiness_v1"},
			{"icon":"🧠", "eyebrow":"角色知识", "title":"角色知道什么，有故事时间边界", "body":"信息存在于系统里不代表角色已经知道。角色行动只能由当前故事时点真正可见、来源明确的证据支持。", "meta":"character evidence contract"},
			{"icon":"📖", "eyebrow":"出版", "title":"接受后的正文保持逐字一致", "body":"Publication IR 核对来源指纹，并在 TXT、Web、Print 与 EPUB 派生过程中保持接受稿 Unicode 正文逐字一致。", "meta":"novelforge_publication_ir_v1"},
			{"icon":"◇", "eyebrow":"运行方式", "title":"能访问，不等于拥有权威", "body":"CLI、本地网页端、云端界面与 Agent Skill 可以开放不同读取能力，但宿主方式不会自动产生 Canon、Framework 或 Settlement 写入权威。", "meta":"authority=false"},
			{"icon":"♡", "eyebrow":"设计系统", "title":"设计系统本身也接受机器检查", "body":"Story Loom 固定 WeiUI 基础，并检查主题、对比度、触控尺寸、语言、减少动画和禁止默认轮询等约束。", "meta":"novelforge_brand_tokens_v2"},
		]
	return [
		{"icon":"🫧", "eyebrow":"Context", "title":"Helpful ≠ actually entered context", "body":"Run receipts distinguish supporting evidence, evidence that actually entered the budgeted packet, and evidence excluded by budget, visibility, or story time.", "meta":"novelforge_run_receipt_v1"},
		{"icon":"✓", "eyebrow":"Readiness", "title":"Every required check binds one candidate", "body":"Missing, pending, or failed surface, reader, continuity, or independent semantic evidence keeps that exact candidate out of user review.", "meta":"novelforge_production_readiness_v1"},
		{"icon":"🧠", "eyebrow":"Character knowledge", "title":"Knowledge has story-time boundaries", "body":"Information existing in the system does not mean a character knows it. Character action must be supported by evidence visible at that story moment.", "meta":"character evidence contract"},
		{"icon":"📖", "eyebrow":"Publication", "title":"Accepted text stays byte-for-byte truthful", "body":"Publication IR verifies source fingerprints and preserves accepted Unicode manuscript text across TXT, Web, Print, and EPUB derivatives.", "meta":"novelforge_publication_ir_v1"},
		{"icon":"◇", "eyebrow":"Hosts", "title":"Reachability never silently becomes authority", "body":"CLI, Local Web, hosted UI, and Agent Skill can expose different read capabilities without manufacturing Canon, Framework, or Settlement write authority.", "meta":"authority=false"},
		{"icon":"♡", "eyebrow":"Design system", "title":"The design system is machine-checked too", "body":"Story Loom pins the WeiUI foundation and checks themes, contrast, touch targets, locales, reduced motion, and the no-default-polling rule.", "meta":"novelforge_brand_tokens_v2"},
	]

func _capability_colors(index: int) -> Array:
	var fills := [C.project_soft, C.runtime_soft, Color("eef6ff"), C.editorial_soft, C.evidence_soft, C.valid_soft]
	var lines := [Color("bedfec"), Color("d2c9ee"), Color("cadff0"), Color("f0ccdc"), Color("edddb8"), Color("cce7dc")]
	return [fills[index % fills.size()], lines[index % lines.size()]]

func _build_lower_sections(y: float, x: float, width: float, phone: bool) -> void:
	var caps := _home_capabilities()
	var kicker := _mixed_label("✦  六条真实产品能力" if _locale == "zh-CN" else "✦  Six real product capabilities", 12, 720, C.runtime)
	kicker.position = Vector2(x, y)
	kicker.size = Vector2(width, 26)
	_stage.add_child(kicker)
	var title_text := "不是 feature list；每一项都对应 current main 里的真实契约。" if _locale == "zh-CN" else "Not a feature wall. Every item maps to a contract on current main."
	var section_title := _label(title_text, 31 if not phone else 27, 760, C.ink)
	section_title.position = Vector2(x, y + 34)
	section_title.size = Vector2(width, 82)
	section_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_stage.add_child(section_title)

	var chip_top := y + 126.0
	if phone:
		for i in range(caps.size()):
			_stage.add_child(_home_capability_chip(Vector2(x, chip_top + i * 92.0), Vector2(width, 80), i, caps[i]))
		var focus_y := chip_top + caps.size() * 92.0 + 18.0
		_build_home_capability_focus(Vector2(x, focus_y), Vector2(width, 348), caps[_home_capability_index], true)
		var lab_y := focus_y + 372.0
		_build_home_labs(Vector2(x, lab_y), width, true)
		var portal_y := lab_y + 704.0
		_build_home_portals(Vector2(x, portal_y), width, true)
		var knowledge_y := portal_y + 736.0
		_build_home_knowledge(Vector2(x, knowledge_y), width, true)
	else:
		var cols := 3
		var gap := 14.0
		var chip_w := (width - gap * 2.0) / 3.0
		for i in range(caps.size()):
			var col := i % cols
			var row := i / cols
			_stage.add_child(_home_capability_chip(Vector2(x + col * (chip_w + gap), chip_top + row * 102.0), Vector2(chip_w, 88), i, caps[i]))
		var focus_y := chip_top + 218.0
		_build_home_capability_focus(Vector2(x, focus_y), Vector2(width, 248), caps[_home_capability_index], false)
		var lab_y := focus_y + 278.0
		_build_home_labs(Vector2(x, lab_y), width, false)
		var portal_y := lab_y + 354.0
		_build_home_portals(Vector2(x, portal_y), width, false)
		var knowledge_y := portal_y + 420.0
		_build_home_knowledge(Vector2(x, knowledge_y), width, false)

func _home_capability_chip(pos: Vector2, chip_size: Vector2, index: int, item: Dictionary) -> Panel:
	var colors := _capability_colors(index)
	var fill: Color = colors[0]
	var border: Color = C.runtime if index == _home_capability_index else colors[1]
	var card := _panel(pos, chip_size, fill, 16, border, 2 if index == _home_capability_index else 1, Color(0.18,0.12,0.24,0.04), 4)
	var icon := _mixed_label(str(item["icon"]), 22, 650, C.runtime)
	icon.position = Vector2(16, 15)
	icon.size = Vector2(36, 32)
	card.add_child(icon)
	var eyebrow := _label(str(item["eyebrow"]), 10, 720, C.muted)
	eyebrow.position = Vector2(56, 13)
	eyebrow.size = Vector2(chip_size.x - 74, 19)
	card.add_child(eyebrow)
	var title := _label(str(item["title"]), 13, 700, C.ink)
	title.position = Vector2(56, 34)
	title.size = Vector2(chip_size.x - 74, chip_size.y - 42)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(title)
	var hit := Button.new()
	hit.text = ""
	hit.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hit.focus_mode = Control.FOCUS_ALL
	hit.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	hit.add_theme_stylebox_override("normal", _button_box(Color(0,0,0,0), 16))
	hit.add_theme_stylebox_override("hover", _button_box(Color(0.48,0.42,0.77,0.05), 16))
	hit.add_theme_stylebox_override("pressed", _button_box(Color(0.48,0.42,0.77,0.09), 16))
	hit.add_theme_stylebox_override("focus", _focus_box(16))
	hit.pressed.connect(_select_home_capability.bind(index))
	card.add_child(hit)
	return card

func _build_home_capability_focus(pos: Vector2, panel_size: Vector2, item: Dictionary, phone: bool) -> void:
	var card := _panel(pos, panel_size, Color("fffdfc"), 22, Color("d8cae8"), 1, Color(0.18,0.12,0.24,0.06), 8)
	_stage.add_child(card)
	var orb_size := 82.0 if phone else 104.0
	var orb := _panel(Vector2(22, 24), Vector2(orb_size, orb_size), C.runtime_soft, int(orb_size / 2.0), Color("d8cae8"), 1)
	var icon := _mixed_label(str(item["icon"]), 34 if phone else 42, 650, C.runtime)
	icon.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	icon.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	orb.add_child(icon)
	card.add_child(orb)
	var copy_x := 22.0 if phone else 150.0
	var copy_y := 128.0 if phone else 28.0
	var eyebrow := _label(str(item["eyebrow"]), 11, 760, C.editorial)
	eyebrow.position = Vector2(copy_x, copy_y)
	eyebrow.size = Vector2(panel_size.x - copy_x - 24, 20)
	card.add_child(eyebrow)
	var title := _label(str(item["title"]), 24 if phone else 28, 760, C.ink)
	title.position = Vector2(copy_x, copy_y + 28)
	title.size = Vector2(panel_size.x - copy_x - 30, 68)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(title)
	var body := _label(str(item["body"]), 14, 430, C.muted)
	body.position = Vector2(copy_x, copy_y + 100)
	body.size = Vector2(panel_size.x - copy_x - 30, 96 if not phone else 116)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_theme_constant_override("line_spacing", 4)
	card.add_child(body)
	var meta := _pill(str(item["meta"]), Vector2(copy_x, panel_size.y - 43), Vector2(min(panel_size.x - copy_x - 30, 285.0), 28), C.surface_soft, C.muted, 10, 560, Color("e3dbe8"))
	card.add_child(meta)
	if not phone:
		var product := _text_button("产品能力 →" if _locale == "zh-CN" else "Product →", Vector2(panel_size.x - 248, panel_size.y - 55), Vector2(108, 38), C.runtime_soft, C.runtime, 12, 650, 10)
		product.pressed.connect(_navigate.bind("/product"))
		card.add_child(product)
		var docs := _text_button("知识库 →" if _locale == "zh-CN" else "Knowledge →", Vector2(panel_size.x - 132, panel_size.y - 55), Vector2(116, 38), Color(0,0,0,0), C.runtime, 12, 620, 10)
		docs.pressed.connect(_navigate.bind("/docs"))
		card.add_child(docs)

func _build_home_labs(pos: Vector2, width: float, phone: bool) -> void:
	var eyebrow := _label("可以直接玩" if _locale == "zh-CN" else "TRY IT", 11, 780, C.editorial)
	eyebrow.position = pos
	eyebrow.size = Vector2(width, 20)
	_stage.add_child(eyebrow)
	var title := _label("别只读介绍，动一下系统边界。" if _locale == "zh-CN" else "Don’t just read the pitch. Touch the boundaries.", 27 if not phone else 24, 760, C.ink)
	title.position = pos + Vector2(0, 26)
	title.size = Vector2(width, 56)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_stage.add_child(title)
	var cards_y := pos.y + 92.0
	if phone:
		_build_context_lab(Vector2(pos.x, cards_y), Vector2(width, 286))
		_build_gate_lab(Vector2(pos.x, cards_y + 304), Vector2(width, 286))
	else:
		var gap := 18.0
		var card_w := (width - gap) / 2.0
		_build_context_lab(Vector2(pos.x, cards_y), Vector2(card_w, 240))
		_build_gate_lab(Vector2(pos.x + card_w + gap, cards_y), Vector2(card_w, 240))

func _build_context_lab(pos: Vector2, panel_size: Vector2) -> void:
	var card := _panel(pos, panel_size, C.runtime_soft, 20, Color("d8cae8"), 1)
	_stage.add_child(card)
	var icon := _mixed_label("🫧", 25, 650, C.runtime)
	icon.position = Vector2(18, 17)
	icon.size = Vector2(34, 30)
	card.add_child(icon)
	var note := _label("示意推演 · authority=false" if _locale == "zh-CN" else "illustrative derivation · authority=false", 10, 600, C.muted)
	note.position = Vector2(58, 17)
	note.size = Vector2(panel_size.x - 130, 18)
	card.add_child(note)
	var title := _label("上下文预算实验" if _locale == "zh-CN" else "Context budget lab", 20, 730, C.ink)
	title.position = Vector2(58, 37)
	title.size = Vector2(panel_size.x - 130, 28)
	card.add_child(title)
	card.add_child(_pill("%d / 5" % _home_budget, Vector2(panel_size.x - 80, 18), Vector2(58, 28), Color("fffdfc"), C.runtime, 11, 700, Color("d8cae8")))
	var strip_x := 18.0
	var strip_y := 88.0
	var gap := 8.0
	var unit_w := (panel_size.x - 36.0 - gap * 4.0) / 5.0
	for i in range(5):
		var active := i < _home_budget
		var unit := _panel(Vector2(strip_x + i * (unit_w + gap), strip_y), Vector2(unit_w, 52), C.runtime if active else Color("fffdfc"), 12, Color("d8cae8"), 1)
		var unit_text := _label(str(i + 1), 12, 700, Color.WHITE if active else C.muted)
		unit_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		unit_text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		unit_text.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		unit.add_child(unit_text)
		card.add_child(unit)
	var minus := _text_button("−", Vector2(18, panel_size.y - 54), Vector2(44, 38), Color("fffdfc"), C.runtime, 18, 700, 10)
	minus.pressed.connect(_adjust_home_budget.bind(-1))
	card.add_child(minus)
	var plus := _text_button("+", Vector2(70, panel_size.y - 54), Vector2(44, 38), C.runtime, Color.WHITE, 18, 700, 10)
	plus.pressed.connect(_adjust_home_budget.bind(1))
	card.add_child(plus)
	var explanation := _label("预算先限制可进入证据的数量，再让模型处理被冻结的 packet。" if _locale == "zh-CN" else "Budget constrains evidence first; the model only sees the frozen packet.", 12, 430, C.muted)
	explanation.position = Vector2(130, panel_size.y - 51)
	explanation.size = Vector2(panel_size.x - 150, 40)
	explanation.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(explanation)

func _build_gate_lab(pos: Vector2, panel_size: Vector2) -> void:
	var card := _panel(pos, panel_size, C.editorial_soft, 20, Color("f0ccdc"), 1)
	_stage.add_child(card)
	var icon := _mixed_label("✓", 25, 700, C.editorial)
	icon.position = Vector2(18, 17)
	icon.size = Vector2(34, 30)
	card.add_child(icon)
	var note := _label("同一候选稿的必要条件" if _locale == "zh-CN" else "same-candidate requirements", 10, 600, C.muted)
	note.position = Vector2(58, 17)
	note.size = Vector2(panel_size.x - 80, 18)
	card.add_child(note)
	var title := _label("候选稿就绪实验" if _locale == "zh-CN" else "Candidate readiness lab", 20, 730, C.ink)
	title.position = Vector2(58, 37)
	title.size = Vector2(panel_size.x - 80, 28)
	card.add_child(title)
	var names := ["Surface", "Reader", "Continuity", "Semantic"]
	var gap := 8.0
	var unit_w := (panel_size.x - 36.0 - gap * 3.0) / 4.0
	for i in range(4):
		var active := bool(_home_gates[i])
		var gate := _text_button(("✓ " if active else "○ ") + names[i], Vector2(18 + i * (unit_w + gap), 88), Vector2(unit_w, 52), C.valid_soft if active else Color("fffdfc"), C.valid if active else C.muted, 11, 650, 10)
		gate.pressed.connect(_toggle_home_gate.bind(i))
		card.add_child(gate)
	var ready := true
	for value in _home_gates:
		if not bool(value):
			ready = false
	var state_text := "可以进入审查 ✨" if ready and _locale == "zh-CN" else ("Ready for review ✨" if ready else ("还差一点点 (´• ω •`)ﾉ" if _locale == "zh-CN" else "Not quite yet (´• ω •`)ﾉ"))
	var state := _panel(Vector2(18, panel_size.y - 70), Vector2(panel_size.x - 36, 50), C.valid_soft if ready else Color("fffdfc"), 14, Color("cce7dc") if ready else Color("e5dce8"), 1)
	var state_label := _mixed_label(state_text, 13, 680, C.valid if ready else C.muted)
	state_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	state_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	state_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	state.add_child(state_label)
	card.add_child(state)

func _build_home_portals(pos: Vector2, width: float, phone: bool) -> void:
	var eyebrow := _label("从一个入口进入整个产品" if _locale == "zh-CN" else "ONE ENTRY POINT INTO THE WHOLE PRODUCT", 11, 780, C.editorial)
	eyebrow.position = pos
	eyebrow.size = Vector2(width, 20)
	_stage.add_child(eyebrow)
	var title := _label("真正的产品入口，不是“继续阅读”。" if _locale == "zh-CN" else "Real product doors, not another ‘read more’.", 27 if not phone else 24, 760, C.ink)
	title.position = pos + Vector2(0, 26)
	title.size = Vector2(width, 56)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_stage.add_child(title)
	var portals := [
		["✦", "Hosted Studio", "真正的只读产品壳；不会假装 Core 已绑定。" if _locale == "zh-CN" else "A real read-only product shell without pretending Core is already bound.", "external"],
		["📚", "知识库" if _locale == "zh-CN" else "Knowledge", "真实文档在构建时进入产品，可搜索、阅读与深链。" if _locale == "zh-CN" else "Real docs are compiled into the product for search, reading, and deep links.", "/docs"],
		["⌘", "架构探索" if _locale == "zh-CN" else "Architecture", "点一个子系统，看它真正负责什么。" if _locale == "zh-CN" else "Pick a subsystem and inspect what it actually owns.", "/architecture"],
		["✧", "出版" if _locale == "zh-CN" else "Publication", "同一份接受稿确定地产生多种派生格式。" if _locale == "zh-CN" else "One accepted manuscript deterministically produces several derivatives.", "/publication"],
	]
	var top := pos.y + 92.0
	if phone:
		for i in range(portals.size()):
			_stage.add_child(_home_portal_card(Vector2(pos.x, top + i * 158.0), Vector2(width, 144), portals[i]))
	else:
		var gap := 16.0
		var card_w := (width - gap) / 2.0
		for i in range(portals.size()):
			var col := i % 2
			var row := i / 2
			_stage.add_child(_home_portal_card(Vector2(pos.x + col * (card_w + gap), top + row * 148.0), Vector2(card_w, 134), portals[i]))

func _home_portal_card(pos: Vector2, card_size: Vector2, portal: Array) -> Panel:
	var card := _panel(pos, card_size, Color("fffdfc"), 18, Color("e8ddea"), 1, Color(0.18,0.12,0.24,0.045), 5)
	var icon_box := _panel(Vector2(16, 18), Vector2(50, 50), C.runtime_soft, 14)
	var icon := _mixed_label(str(portal[0]), 24, 650, C.runtime)
	icon.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	icon.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	icon_box.add_child(icon)
	card.add_child(icon_box)
	var title := _label(str(portal[1]), 17, 730, C.ink)
	title.position = Vector2(80, 18)
	title.size = Vector2(card_size.x - 112, 25)
	card.add_child(title)
	var body := _label(str(portal[2]), 12, 430, C.muted)
	body.position = Vector2(80, 49)
	body.size = Vector2(card_size.x - 112, card_size.y - 62)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_theme_constant_override("line_spacing", 3)
	card.add_child(body)
	var arrow := _mixed_label("↗" if str(portal[3]) == "external" else "→", 18, 700, C.runtime)
	arrow.position = Vector2(card_size.x - 30, 20)
	arrow.size = Vector2(18, 24)
	card.add_child(arrow)
	var hit := Button.new()
	hit.text = ""
	hit.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hit.focus_mode = Control.FOCUS_ALL
	hit.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	hit.add_theme_stylebox_override("normal", _button_box(Color(0,0,0,0), 18))
	hit.add_theme_stylebox_override("hover", _button_box(Color(0.48,0.42,0.77,0.045), 18))
	hit.add_theme_stylebox_override("focus", _focus_box(18))
	if str(portal[3]) == "external":
		hit.pressed.connect(_open_external.bind(STUDIO_URL))
	else:
		hit.pressed.connect(_navigate.bind(str(portal[3])))
	card.add_child(hit)
	return card

func _build_home_knowledge(pos: Vector2, width: float, phone: bool) -> void:
	var section_h := 530.0 if phone else 360.0
	var section := _panel(pos, Vector2(width, section_h), Color("f8fbff"), 22, Color("d7e6ee"), 1)
	_stage.add_child(section)
	var copy_w := width - 36.0 if phone else width * 0.42
	var copy := Control.new()
	copy.position = Vector2(22, 22)
	copy.size = Vector2(copy_w - 22, 300)
	section.add_child(copy)
	var sticker := _mixed_label("📚✨", 26, 650, C.runtime)
	sticker.position = Vector2(0, 0)
	sticker.size = Vector2(72, 32)
	copy.add_child(sticker)
	var eyebrow := _label("知识库" if _locale == "zh-CN" else "KNOWLEDGE", 11, 760, C.project)
	eyebrow.position = Vector2(0, 46)
	eyebrow.size = Vector2(copy.size.x, 20)
	copy.add_child(eyebrow)
	var title := _label("真实文档已经进入产品本身" if _locale == "zh-CN" else "Real documentation now lives inside the product", 25 if phone else 28, 760, C.ink)
	title.position = Vector2(0, 72)
	title.size = Vector2(copy.size.x, 80)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	copy.add_child(title)
	var body := _label("文档在构建时从仓库权威源编译进站点。可以搜索、阅读、深链，不需要先跳去 GitHub。" if _locale == "zh-CN" else "Docs are compiled at build time from repository authority into the site. Search, read, and deep-link without leaving for GitHub first.", 13, 430, C.muted)
	body.position = Vector2(0, 160)
	body.size = Vector2(copy.size.x, 82)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_theme_constant_override("line_spacing", 4)
	copy.add_child(body)
	var open_docs := _text_button("打开文档 →" if _locale == "zh-CN" else "Open document →", Vector2(0, 255), Vector2(148, 42), C.runtime, Color.WHITE, 13, 650, 10)
	open_docs.pressed.connect(_navigate.bind("/docs"))
	copy.add_child(open_docs)
	var list_pos := Vector2(22, 336) if phone else Vector2(width * 0.46, 22)
	var list_size := Vector2(width - 44, 170) if phone else Vector2(width * 0.54 - 22, section_h - 44)
	var list := _panel(list_pos, list_size, Color("fffdfc"), 18, Color("dbe4ea"), 1)
	section.add_child(list)
	var meta := _label("Tier A · build-time · authority=false", 10, 620, C.muted)
	meta.position = Vector2(16, 14)
	meta.size = Vector2(list_size.x - 32, 18)
	list.add_child(meta)
	var docs := [
		["START_HERE", "从最短路径进入 NovelForge 的权威文档。" if _locale == "zh-CN" else "The shortest authoritative way into NovelForge."],
		["Architecture", "看 Project、Context、Gate 与 Settlement 如何分工。" if _locale == "zh-CN" else "See how Project, Context, Gate, and Settlement divide ownership."],
		["Publication", "接受稿如何进入确定性的出版派生链。" if _locale == "zh-CN" else "How accepted text enters deterministic publication derivation."],
	]
	var row_h := (list_size.y - 44.0) / 3.0
	for i in range(docs.size()):
		var row := _panel(Vector2(12, 38 + i * row_h), Vector2(list_size.x - 24, row_h - 6), Color("fffdfc"), 10, Color("e7edf0"), 1)
		var strong := _label(str(docs[i][0]), 12, 700, C.ink)
		strong.position = Vector2(12, 8)
		strong.size = Vector2(row.size.x - 38, 20)
		row.add_child(strong)
		var small := _label(str(docs[i][1]), 10, 430, C.muted)
		small.position = Vector2(12, 29)
		small.size = Vector2(row.size.x - 38, row.size.y - 34)
		small.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		row.add_child(small)
		var arrow := _label("→", 14, 700, C.runtime)
		arrow.position = Vector2(row.size.x - 24, 11)
		arrow.size = Vector2(16, 20)
		row.add_child(arrow)
		list.add_child(row)

func _select_home_capability(index: int) -> void:
	_home_capability_index = clampi(index, 0, 5)
	_queue_rebuild_preserve_scroll()

func _adjust_home_budget(delta: int) -> void:
	_home_budget = clampi(_home_budget + delta, 1, 5)
	_queue_rebuild_preserve_scroll()

func _toggle_home_gate(index: int) -> void:
	if index >= 0 and index < _home_gates.size():
		_home_gates[index] = not bool(_home_gates[index])
		_queue_rebuild_preserve_scroll()

# -----------------------------------------------------------------------------
# Architecture: fix Chinese hero collision and restore the missing inspector
# body that exists below the execution-path canvas in the golden fixture.
# -----------------------------------------------------------------------------

func _architecture_nodes() -> Array:
	if _locale == "zh-CN":
		return [
			{"icon":"⌂","title":"Project","desc":"项目层固定正典、计划、角色、关系、研究资料与当前工作的权威边界。","inputs":"project files\nlock + attestation\naccepted state","outputs":"authority map\nproject identity\nactive work","authority":"Project 不能被一次模型输出覆盖。","contracts":"Project schema\nnovelforge.lock.json"},
			{"icon":"✦","title":"Manager","desc":"Manager 建立 run、决定当前 task mode，并把一次执行需要的状态组织成可检查的运行身份。","inputs":"task intent\nproject identity\nruntime policy","outputs":"manager run\nmode\nrouting","authority":"Manager 编排执行，但不拥有 Canon。","contracts":"Session Runtime\nRuntime Routing"},
			{"icon":"◉","title":"Context","desc":"Context 先做可见性、故事时间、权威与预算过滤，再形成冻结后的活动上下文包。","inputs":"eligible evidence\nvisibility\nstory time","outputs":"frozen packet\nexclusion reasons\nreceipt","authority":"相关 ≠ 可见；可见 ≠ 已进入。","contracts":"Context protocol\nrun receipt"},
			{"icon":"⌘","title":"Worker","desc":"Worker 在给定 task mode 与冻结上下文内执行创作或分析，不越过控制平面边界。","inputs":"task mode\nfrozen context\ncapabilities","outputs":"candidate\nanalysis\nevidence","authority":"Worker 输出默认不是已接受事实。","contracts":"Semantic Execution\nWorker contract"},
			{"icon":"✓","title":"Gate","desc":"Gate 围绕同一个 exact candidate fingerprint 汇合必要的确定性与语义证据。","inputs":"candidate fingerprint\ndeterministic checks\nsemantic evidence","outputs":"gate status\nblocking evidence\nreadiness","authority":"Production readiness 不是 Canon acceptance。","contracts":"novelforge_production_readiness_v1"},
			{"icon":"◇","title":"Settlement","desc":"Settlement 只在接受之后，通过 Core-owned 语义把 eligible state changes 精确提交。","inputs":"accepted decision\nstate changes\nprovenance","outputs":"settlement receipt\ncommitted transition","authority":"UI 不能制造 settlement authority。","contracts":"Control Plane lineage"},
			{"icon":"📖","title":"Publication","desc":"Publication 把 accepted manuscript 确定性编译成带 provenance 的派生出版物。","inputs":"accepted manuscript\npublication profile","outputs":"TXT\nWeb\nPrint\nEPUB 3.3","authority":"Publication artifact 是 derived，authority=false。","contracts":"novelforge_publication_ir_v1\npublication/compiler.py"},
		]
	return [
		{"icon":"⌂","title":"Project","desc":"Pins Canon, plans, character state, research, and active-work authority boundaries.","inputs":"project files\nlock + attestation\naccepted state","outputs":"authority map\nproject identity\nactive work","authority":"A single model output cannot overwrite Project authority.","contracts":"Project schema\nnovelforge.lock.json"},
		{"icon":"✦","title":"Manager","desc":"Creates a run, selects one task mode, and gives the execution a durable inspectable identity.","inputs":"task intent\nproject identity\nruntime policy","outputs":"manager run\nmode\nrouting","authority":"Manager orchestrates execution; it does not own Canon.","contracts":"Session Runtime\nRuntime Routing"},
		{"icon":"◉","title":"Context","desc":"Filters visibility, story time, authority, and budget before freezing the active context packet.","inputs":"eligible evidence\nvisibility\nstory time","outputs":"frozen packet\nexclusion reasons\nreceipt","authority":"Relevant ≠ visible; visible ≠ entered.","contracts":"Context protocol\nrun receipt"},
		{"icon":"⌘","title":"Worker","desc":"Executes creation or analysis inside one task mode and one frozen context without crossing control-plane boundaries.","inputs":"task mode\nfrozen context\ncapabilities","outputs":"candidate\nanalysis\nevidence","authority":"Worker output is not accepted truth by default.","contracts":"Semantic Execution\nWorker contract"},
		{"icon":"✓","title":"Gate","desc":"Conjoins deterministic and semantic evidence around one exact candidate fingerprint.","inputs":"candidate fingerprint\ndeterministic checks\nsemantic evidence","outputs":"gate status\nblocking evidence\nreadiness","authority":"Production readiness is gate evidence, not Canon acceptance.","contracts":"novelforge_production_readiness_v1"},
		{"icon":"◇","title":"Settlement","desc":"Applies eligible state changes only after acceptance through Core-owned settlement semantics.","inputs":"accepted decision\nstate changes\nprovenance","outputs":"settlement receipt\ncommitted transition","authority":"The UI cannot manufacture settlement authority.","contracts":"Control Plane lineage"},
		{"icon":"📖","title":"Publication","desc":"Compiles accepted manuscript text deterministically into provenance-bound derived artifacts.","inputs":"accepted manuscript\npublication profile","outputs":"TXT\nWeb\nPrint\nEPUB 3.3","authority":"Publication artifacts are derived and authority=false.","contracts":"novelforge_publication_ir_v1\npublication/compiler.py"},
	]

func _patch_architecture_copy_geometry() -> void:
	if _locale != "zh-CN":
		return
	var title := _find_label_prefix(self, "看一次 NovelForge")
	if title != null:
		title.size.y = 222.0 if _layout != "phone" else 190.0
		title.add_theme_constant_override("line_spacing", -2 if _layout != "phone" else -4)
	var lede := _find_label_prefix(self, "Project → Manager")
	if lede != null:
		lede.position.y = 306.0 if _layout != "phone" else 286.0
		lede.size.y = 78.0 if _layout != "phone" else 122.0
	var docs := _find_button_exact(self, "📚 阅读架构文档")
	if docs == null:
		docs = _find_button_exact(self, "阅读架构文档")
	if docs != null:
		docs.position.y = 382.0 if _layout != "phone" else 414.0
	var play := _find_button_exact(self, "▷ Playground")
	if play != null:
		play.position.y = 382.0 if _layout != "phone" else 468.0

func _append_architecture_inspector() -> void:
	if _stage == null:
		return
	var phone := _layout == "phone"
	var page_x := 16.0 if phone else (40.0 if _layout == "compact" else 70.0)
	var width := size.x - page_x * 2.0
	var top := 1668.0 if phone else 1008.0
	var nodes := _architecture_nodes()
	var eyebrow := _label("节点检查器" if _locale == "zh-CN" else "NODE INSPECTOR", 11, 780, C.editorial)
	eyebrow.position = Vector2(page_x, top)
	eyebrow.size = Vector2(width, 20)
	_stage.add_child(eyebrow)
	var title := _label("选择一个节点，看输入、输出、权威与契约。" if _locale == "zh-CN" else "Select a node: inputs, outputs, authority, contracts.", 25 if phone else 28, 760, C.ink)
	title.position = Vector2(page_x, top + 26)
	title.size = Vector2(width, 58)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_stage.add_child(title)
	var selectors_y := top + 92.0
	if phone:
		var selector_w := (width - 10.0) / 2.0
		for i in range(nodes.size()):
			var col := i % 2
			var row := i / 2
			var button := _mixed_text_button("%s  %s" % [str(nodes[i]["icon"]), str(nodes[i]["title"])], Vector2(page_x + col * (selector_w + 10), selectors_y + row * 52.0), Vector2(selector_w, 44), C.runtime_soft if i == _architecture_selected else Color("fffdfc"), C.runtime if i == _architecture_selected else C.ink, 12, 650, 10)
			button.pressed.connect(_select_architecture_node.bind(i))
			_stage.add_child(button)
		var detail_y := selectors_y + 4 * 52.0 + 18.0
		_build_architecture_detail(Vector2(page_x, detail_y), Vector2(width, 410), nodes[_architecture_selected])
		_build_architecture_trace(Vector2(page_x, detail_y + 430), Vector2(width, 430), nodes)
		_stage.custom_minimum_size.y = max(_stage.custom_minimum_size.y, detail_y + 900)
	else:
		var gap := 8.0
		var selector_w := (width - gap * 6.0) / 7.0
		for i in range(nodes.size()):
			var button := _mixed_text_button("%s %s" % [str(nodes[i]["icon"]), str(nodes[i]["title"])], Vector2(page_x + i * (selector_w + gap), selectors_y), Vector2(selector_w, 46), C.runtime_soft if i == _architecture_selected else Color("fffdfc"), C.runtime if i == _architecture_selected else C.ink, 11, 650, 9)
			button.pressed.connect(_select_architecture_node.bind(i))
			_stage.add_child(button)
		var detail_y := selectors_y + 66.0
		var left_w := width * 0.64
		_build_architecture_detail(Vector2(page_x, detail_y), Vector2(left_w, 410), nodes[_architecture_selected])
		_build_architecture_trace(Vector2(page_x + left_w + 18, detail_y), Vector2(width - left_w - 18, 410), nodes)
		_stage.custom_minimum_size.y = max(_stage.custom_minimum_size.y, detail_y + 460)

func _build_architecture_detail(pos: Vector2, panel_size: Vector2, node: Dictionary) -> void:
	var card := _panel(pos, panel_size, Color("fffdfc"), 20, Color("d8cae8"), 1)
	_stage.add_child(card)
	var icon := _mixed_label(str(node["icon"]), 30, 700, C.runtime)
	icon.position = Vector2(20, 20)
	icon.size = Vector2(42, 38)
	card.add_child(icon)
	var small := _label("当前节点" if _locale == "zh-CN" else "SELECTED NODE", 10, 760, C.muted)
	small.position = Vector2(72, 20)
	small.size = Vector2(panel_size.x - 92, 18)
	card.add_child(small)
	var title := _label(str(node["title"]), 24, 760, C.ink)
	title.position = Vector2(72, 40)
	title.size = Vector2(panel_size.x - 92, 34)
	card.add_child(title)
	var desc := _label(str(node["desc"]), 13, 430, C.muted)
	desc.position = Vector2(20, 88)
	desc.size = Vector2(panel_size.x - 40, 64)
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.add_theme_constant_override("line_spacing", 4)
	card.add_child(desc)
	var col_w := (panel_size.x - 58.0) / 2.0
	_build_architecture_field(card, Vector2(20, 164), Vector2(col_w, 92), "输入" if _locale == "zh-CN" else "INPUTS", str(node["inputs"]))
	_build_architecture_field(card, Vector2(38 + col_w, 164), Vector2(col_w, 92), "输出" if _locale == "zh-CN" else "OUTPUTS", str(node["outputs"]))
	_build_architecture_field(card, Vector2(20, 270), Vector2(col_w, 116), "AUTHORITY", str(node["authority"]))
	_build_architecture_field(card, Vector2(38 + col_w, 270), Vector2(col_w, 116), "CONTRACTS", str(node["contracts"]))

func _build_architecture_field(parent: Control, pos: Vector2, field_size: Vector2, heading: String, body_text: String) -> void:
	var field := _panel(pos, field_size, C.surface_soft, 12, Color("e8ddea"), 1)
	parent.add_child(field)
	var heading_label := _label(heading, 9, 760, C.runtime)
	heading_label.position = Vector2(12, 10)
	heading_label.size = Vector2(field_size.x - 24, 18)
	field.add_child(heading_label)
	var body := _label(body_text, 11, 500, C.ink)
	body.position = Vector2(12, 31)
	body.size = Vector2(field_size.x - 24, field_size.y - 40)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_theme_constant_override("line_spacing", 3)
	field.add_child(body)

func _build_architecture_trace(pos: Vector2, panel_size: Vector2, nodes: Array) -> void:
	var card := _panel(pos, panel_size, Color("fffdfc"), 20, Color("e8ddea"), 1)
	_stage.add_child(card)
	var small := _label("模拟 TRACE" if _locale == "zh-CN" else "PREVIEW TRACE", 10, 760, C.muted)
	small.position = Vector2(18, 18)
	small.size = Vector2(panel_size.x - 36, 18)
	card.add_child(small)
	var title := _label("只展示公开可观察边界" if _locale == "zh-CN" else "Public observable boundaries only", 17, 730, C.ink)
	title.position = Vector2(18, 40)
	title.size = Vector2(panel_size.x - 36, 28)
	card.add_child(title)
	var next_text := "模拟一次 run" if _architecture_run_step < 0 and _locale == "zh-CN" else ("Simulate a run" if _architecture_run_step < 0 else ("下一步" if _locale == "zh-CN" else "Next step"))
	var next := _text_button(next_text, Vector2(18, 78), Vector2(130, 38), C.runtime, Color.WHITE, 12, 650, 9)
	next.pressed.connect(_advance_architecture_run)
	card.add_child(next)
	var reset := _text_button("重置" if _locale == "zh-CN" else "Reset", Vector2(156, 78), Vector2(76, 38), Color(0,0,0,0), C.runtime, 12, 620, 9)
	reset.pressed.connect(_reset_architecture_run)
	card.add_child(reset)
	var y := 132.0
	var row_h := (panel_size.y - y - 16.0) / 7.0
	for i in range(nodes.size()):
		var state := "pending"
		if _architecture_run_step >= 0:
			state = "passed" if i < _architecture_run_step else ("current" if i == _architecture_run_step else "pending")
		var row := _panel(Vector2(16, y + i * row_h), Vector2(panel_size.x - 32, row_h - 5), C.valid_soft if state == "passed" else (C.runtime_soft if state == "current" else Color("fffdfc")), 9, Color("e8ddea"), 1)
		var marker := _mixed_label("✓" if state == "passed" else ("●" if state == "current" else "%02d" % (i + 1)), 11, 700, C.valid if state == "passed" else (C.runtime if state == "current" else C.muted))
		marker.position = Vector2(10, 7)
		marker.size = Vector2(28, 20)
		row.add_child(marker)
		var name := _label(str(nodes[i]["title"]), 11, 650, C.ink)
		name.position = Vector2(42, 7)
		name.size = Vector2(row.size.x - 112, 20)
		row.add_child(name)
		var status := _label(state, 9, 560, C.muted)
		status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		status.position = Vector2(row.size.x - 72, 7)
		status.size = Vector2(60, 20)
		row.add_child(status)
		card.add_child(row)

func _select_architecture_node(index: int) -> void:
	_architecture_selected = clampi(index, 0, 6)
	_queue_rebuild_preserve_scroll()

func _advance_architecture_run() -> void:
	_architecture_run_step = min(_architecture_run_step + 1, 6)
	_architecture_selected = max(_architecture_run_step, 0)
	_queue_rebuild_preserve_scroll()

func _reset_architecture_run() -> void:
	_architecture_run_step = -1
	_queue_rebuild_preserve_scroll()

# -----------------------------------------------------------------------------
# Publication: the previous implementation stopped after the READING PREVIEW
# heading. Replace the format rail and preview with a real selectable workbench
# and provenance surface.
# -----------------------------------------------------------------------------

func _publication_profiles() -> Array:
	if _locale == "zh-CN":
		return [
			{"id":"TXT","label":"纯文本","title":"只保留正文，不叠加表现层","artifact":".txt"},
			{"id":"WEB","label":"网页","title":"适配屏幕的阅读表面","artifact":".html + .css"},
			{"id":"PRINT","label":"印刷版","title":"面向纸面的分页排版","artifact":"print HTML/CSS"},
			{"id":"EPUB","label":"EPUB","title":"可重排的电子书包","artifact":".epub"},
		]
	return [
		{"id":"TXT","label":"Clean text","title":"Exact text, no presentation layer","artifact":".txt"},
		{"id":"WEB","label":"Web","title":"Responsive reading surface","artifact":".html + .css"},
		{"id":"PRINT","label":"Print","title":"Paged-media composition","artifact":"print HTML/CSS"},
		{"id":"EPUB","label":"EPUB","title":"Reflowable ebook package","artifact":".epub"},
	]

func _build_format_strip(pos: Vector2, strip_size: Vector2, phone: bool) -> void:
	var profiles := _publication_profiles()
	var actual_h := 330.0 if phone else 118.0
	var strip := _panel(pos, Vector2(strip_size.x, actual_h), Color("fffdfc"), 18, Color("e8ddea"), 1)
	_stage.add_child(strip)
	if phone:
		for i in range(profiles.size()):
			var p: Dictionary = profiles[i]
			var button := _text_button("%s   %s\n%s" % [str(p["id"]), str(p["label"]), str(p["title"])], Vector2(14, 14 + i * 76), Vector2(strip_size.x - 28, 66), C.runtime_soft if i == _publication_profile else Color("fffdfc"), C.runtime if i == _publication_profile else C.ink, 11, 650, 11)
			button.alignment = HORIZONTAL_ALIGNMENT_LEFT
			button.pressed.connect(_select_publication_profile.bind(i))
			strip.add_child(button)
	else:
		var intro_w := 190.0
		var intro := _label("出版工作台" if _locale == "zh-CN" else "Publication\nworkbench", 14, 720, C.ink)
		intro.position = Vector2(20, 24)
		intro.size = Vector2(intro_w - 30, 60)
		strip.add_child(intro)
		var cell_w := (strip_size.x - intro_w) / 4.0
		for i in range(profiles.size()):
			var p: Dictionary = profiles[i]
			var button := _text_button("%s\n%s\n%s" % [str(p["id"]), str(p["title"]), str(p["artifact"])], Vector2(intro_w + i * cell_w, 0), Vector2(cell_w, actual_h), C.runtime_soft if i == _publication_profile else Color("fffdfc"), C.runtime if i == _publication_profile else C.ink, 10, 650, 0)
			button.alignment = HORIZONTAL_ALIGNMENT_LEFT
			button.pressed.connect(_select_publication_profile.bind(i))
			strip.add_child(button)

func _build_reading_preview(pos: Vector2, preview_size: Vector2, phone: bool) -> void:
	var profiles := _publication_profiles()
	var profile: Dictionary = profiles[_publication_profile]
	var h := 650.0 if phone else 470.0
	var preview := _panel(pos, Vector2(preview_size.x, h), Color("fffdfc"), 22, Color("e8ddea"), 1)
	_stage.add_child(preview)
	var heart := _mixed_label("♡", 17, 650, C.editorial)
	heart.position = Vector2(18, 18)
	heart.size = Vector2(24, 24)
	preview.add_child(heart)
	var label := _label("阅读预览" if _locale == "zh-CN" else "READING PREVIEW", 10, 760, C.muted)
	label.position = Vector2(58, 17)
	label.size = Vector2(180, 20)
	preview.add_child(label)
	var title := _label(str(profile["label"]), 17, 720, C.ink)
	title.position = Vector2(58, 40)
	title.size = Vector2(220, 25)
	preview.add_child(title)
	preview.add_child(_pill("exact text", Vector2(preview_size.x - 190, 18), Vector2(82, 26), C.valid_soft, C.valid, 9, 650, Color("cce7dc")))
	preview.add_child(_pill("preview only", Vector2(preview_size.x - 102, 18), Vector2(84, 26), C.surface_soft, C.muted, 9, 620, Color("e8ddea")))

	if phone:
		_build_publication_page(preview, Vector2(18, 82), Vector2(preview_size.x - 36, 320), profile, true)
		_build_publication_metadata(preview, Vector2(18, 420), Vector2(preview_size.x - 36, 210), profile)
		_build_publication_provenance(pos + Vector2(0, h + 22), Vector2(preview_size.x, 440), profile, true)
	else:
		var page_w := preview_size.x * 0.61
		_build_publication_page(preview, Vector2(24, 82), Vector2(page_w - 36, h - 110), profile, false)
		_build_publication_metadata(preview, Vector2(page_w, 82), Vector2(preview_size.x - page_w - 24, h - 110), profile)
		_build_publication_provenance(pos + Vector2(0, h + 22), Vector2(preview_size.x, 190), profile, false)

func _build_publication_page(parent: Control, pos: Vector2, page_size: Vector2, profile: Dictionary, phone: bool) -> void:
	var bg := Color("fffdfa")
	if str(profile["id"]) == "WEB":
		bg = Color("eef8fb")
	elif str(profile["id"]) == "PRINT":
		bg = C.evidence_soft
	elif str(profile["id"]) == "EPUB":
		bg = C.editorial_soft
	var device := _panel(pos, page_size, bg, 18, Color("d8cae0"), 1, Color(0.18,0.12,0.24,0.05), 5)
	parent.add_child(device)
	var badge := _pill(str(profile["id"]), Vector2(14, 12), Vector2(60, 26), Color("fffdfc"), C.editorial, 9, 720, Color("e4d8df"))
	device.add_child(badge)
	var page_margin := 34.0 if phone else 58.0
	var page := _panel(Vector2(page_margin, 52), Vector2(page_size.x - page_margin * 2.0, page_size.y - 76), Color("fffdfc"), 8, Color("ddd4df"), 1)
	device.add_child(page)
	var meta := _label("NovelForge · %s" % str(profile["id"]), 9, 620, C.muted)
	meta.position = Vector2(18, 14)
	meta.size = Vector2(page.size.x - 36, 18)
	page.add_child(meta)
	var chapter := _label("第一章 · 夜幕与灯火" if _locale == "zh-CN" else "Chapter 1 · Nightfall and lights", 17 if phone else 19, 740, C.ink)
	chapter.position = Vector2(18, 42)
	chapter.size = Vector2(page.size.x - 36, 34)
	chapter.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	page.add_child(chapter)
	var p1 := _label("夜幕降临，城市的灯光一盏盏亮起，像星星坠落在河面上。" if _locale == "zh-CN" else "Night fell and city lights came on one by one, like stars settling on the river.", 12 if phone else 13, 430, C.ink)
	p1.position = Vector2(18, 92)
	p1.size = Vector2(page.size.x - 36, 68)
	p1.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	p1.add_theme_constant_override("line_spacing", 5)
	page.add_child(p1)
	var p2 := _label("他站在桥边，手里握着一封信，风从河面吹来。" if _locale == "zh-CN" else "He stood by the bridge holding a letter while wind moved across the river.", 12 if phone else 13, 430, C.ink)
	p2.position = Vector2(18, 172)
	p2.size = Vector2(page.size.x - 36, 68)
	p2.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	p2.add_theme_constant_override("line_spacing", 5)
	page.add_child(p2)

func _build_publication_metadata(parent: Control, pos: Vector2, panel_size: Vector2, profile: Dictionary) -> void:
	var card := _panel(pos, panel_size, C.surface_soft, 16, Color("e8ddea"), 1)
	parent.add_child(card)
	var small := _label("格式配置与元数据" if _locale == "zh-CN" else "PROFILE & METADATA", 9, 760, C.muted)
	small.position = Vector2(16, 15)
	small.size = Vector2(panel_size.x - 32, 18)
	card.add_child(small)
	var title := _label(str(profile["title"]), 16, 720, C.ink)
	title.position = Vector2(16, 39)
	title.size = Vector2(panel_size.x - 32, 56)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(title)
	var fields := [["artifact", str(profile["artifact"])], ["source", "sha256 · exact"], ["authority", "false"], ["render", "deterministic"]]
	var y := 112.0
	for field in fields:
		var row := _panel(Vector2(14, y), Vector2(panel_size.x - 28, 42), Color("fffdfc"), 9, Color("e6dfe9"), 1)
		var key := _label(str(field[0]), 9, 620, C.muted)
		key.position = Vector2(10, 11)
		key.size = Vector2(78, 20)
		row.add_child(key)
		var value := _label(str(field[1]), 10, 680, C.ink)
		value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		value.position = Vector2(90, 11)
		value.size = Vector2(row.size.x - 100, 20)
		row.add_child(value)
		card.add_child(row)
		y += 48.0

func _build_publication_provenance(pos: Vector2, panel_size: Vector2, profile: Dictionary, phone: bool) -> void:
	var card := _panel(pos, panel_size, Color("fffdfc"), 20, Color("e8ddea"), 1)
	_stage.add_child(card)
	var small := _label("PROVENANCE", 10, 760, C.muted)
	small.position = Vector2(18, 16)
	small.size = Vector2(panel_size.x - 36, 18)
	card.add_child(small)
	var title := _label("每个派生物都能回到同一份接受正文。" if _locale == "zh-CN" else "Every derivative resolves back to the same accepted manuscript.", 17, 720, C.ink)
	title.position = Vector2(18, 39)
	title.size = Vector2(panel_size.x - 36, 48)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(title)
	var nodes := [["✓","ACCEPTED","Accepted manuscript","sha256 · exact"], ["IR","PUBLICATION IR","novelforge_publication_ir_v1","schema-bound"], ["⌘","COMPILER","publication/compiler.py","deterministic"], [str(profile["id"]),"ARTIFACT",str(profile["artifact"]),"authority=false"]]
	if phone:
		var y := 104.0
		for item in nodes:
			var row := _panel(Vector2(16, y), Vector2(panel_size.x - 32, 70), C.surface_soft, 11, Color("e8ddea"), 1)
			var icon := _mixed_label(str(item[0]), 14, 700, C.runtime)
			icon.position = Vector2(12, 13)
			icon.size = Vector2(36, 24)
			row.add_child(icon)
			var heading := _label(str(item[1]), 9, 700, C.muted)
			heading.position = Vector2(52, 10)
			heading.size = Vector2(row.size.x - 64, 18)
			row.add_child(heading)
			var value := _label(str(item[2]) + "  ·  " + str(item[3]), 10, 620, C.ink)
			value.position = Vector2(52, 31)
			value.size = Vector2(row.size.x - 64, 28)
			value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			row.add_child(value)
			card.add_child(row)
			y += 78.0
	else:
		var gap := 12.0
		var node_w := (panel_size.x - 36.0 - gap * 3.0) / 4.0
		for i in range(nodes.size()):
			var item = nodes[i]
			var node := _panel(Vector2(18 + i * (node_w + gap), 102), Vector2(node_w, 70), C.surface_soft, 11, Color("e8ddea"), 1)
			var icon := _mixed_label(str(item[0]), 12, 700, C.runtime)
			icon.position = Vector2(10, 10)
			icon.size = Vector2(42, 20)
			node.add_child(icon)
			var heading := _label(str(item[1]), 8, 700, C.muted)
			heading.position = Vector2(52, 9)
			heading.size = Vector2(node_w - 62, 18)
			node.add_child(heading)
			var value := _label(str(item[2]), 9, 650, C.ink)
			value.position = Vector2(10, 34)
			value.size = Vector2(node_w - 20, 18)
			node.add_child(value)
			var meta := _label(str(item[3]), 8, 520, C.muted)
			meta.position = Vector2(10, 52)
			meta.size = Vector2(node_w - 20, 15)
			node.add_child(meta)
			card.add_child(node)

func _select_publication_profile(index: int) -> void:
	_publication_profile = clampi(index, 0, 3)
	_queue_rebuild_preserve_scroll()

# -----------------------------------------------------------------------------
# Shared event-driven rebuild helper. It preserves the current internal Godot
# scroll position so interactive cards do not throw the reader back to the top.
# -----------------------------------------------------------------------------

func _queue_rebuild_preserve_scroll() -> void:
	var y := 0
	if _scroll != null:
		y = _scroll.scroll_vertical
	call_deferred("_rebuild_at_scroll", y)

func _rebuild_at_scroll(scroll_y: int) -> void:
	_build()
	if _scroll != null:
		_scroll.scroll_vertical = scroll_y
	_publish_ready()
