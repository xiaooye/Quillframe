extends "res://scripts/main_parity.gd"

func _build_product_hero(pos: Vector2, hero_size: Vector2, stacked: bool) -> void:
	var hero := _panel(pos, hero_size, Color("fffdfc"), 28 if not stacked else 22, Color("e8ddea"), 1, Color(0.18,0.12,0.24,0.09), 12)
	_stage.add_child(hero)
	var inner := _panel(Vector2(8 if not stacked else 6, 8 if not stacked else 6), hero_size - Vector2(16 if not stacked else 12, 16 if not stacked else 12), Color(0,0,0,0), 20 if not stacked else 16, Color(0.95,0.74,0.84,0.30), 1)
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
	var title_y := pad + 12.0 if not stacked else pad + 20.0
	if _locale == "zh-CN":
		title_text = "NovelForge 是小说生产系统，\n不是提示词外壳。" if not stacked else "NovelForge 是小说\n生产系统，不是\n提示词外壳。"
		title_size = 54 if not stacked else 39
		title_box = Vector2(610 if not stacked else hero_size.x - pad * 2.0, 190 if not stacked else 150)
	else:
		title_text = "NovelForge is a\nfiction production\nsystem, not a\nprompt wrapper." if not stacked else "NovelForge\nis a fiction\nproduction\nsystem, not\na prompt\nwrapper."
		title_size = 62 if not stacked else 39
		title_box = Vector2(610 if not stacked else hero_size.x - pad * 2.0, 260 if not stacked else 240)
	var title := _label(title_text, title_size, 780 if _locale == "en-US" else 720, C.ink)
	title.position = Vector2(pad, title_y)
	title.size = title_box
	title.scale = Vector2(1.055 if not stacked and _locale == "en-US" else 1.0, 1.0)
	title.add_theme_constant_override("line_spacing", -26 if not stacked and _locale == "en-US" else (-16 if stacked and _locale == "en-US" else -9))
	hero.add_child(title)

	var lede_text := ""
	if _locale == "zh-CN":
		lede_text = "它把创作判断与确定性控制分开，让一本长期运行的书能持续积累证据、\n修订和状态，而不是把每一次模型输出都顺手升级成事实。" if not stacked else "它把创作判断与确定性控制分开，让一本长期运行的书能持续积累证据、修订和状态，而不是把每一次模型输出都顺手升级成事实。"
	else:
		lede_text = "It separates creative judgment from deterministic control so a long-\nrunning book can accumulate evidence, revisions, and state without\nturning every previous model output into truth." if not stacked else "It separates creative judgment from\ndeterministic control so a long-running\nbook can accumulate evidence, revisions,\nand state without turning every previous\nmodel output into truth."
	var lede := _label(lede_text, 17 if not stacked else 16, 420, C.muted)
	lede.position = Vector2(pad, 346.0 if not stacked else (310.0 if _locale == "en-US" else 220.0))
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
	var stack := _panel(pos, stack_size, Color("fbf9fd"), 22, Color("eee5f0"), 1, Color(0.18,0.12,0.24,0.04), 5)
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
	var row_x := 50.0 if not phone else 20.0
	var row_y := 64.0 if not phone else 18.0
	var row_h := 47.0
	var row_gap := 7.0
	var base_w := stack_size.x - (130.0 if not phone else 68.0)
	for i in range(names.size()):
		var shift: float = shifts[i]
		var row := _panel(Vector2(row_x + shift, row_y + i * (row_h + row_gap)), Vector2(base_w, row_h), Color("fffdfc"), 12, Color("e7deea"), 1, Color(0.18,0.12,0.24,0.045), 4)
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

func _product_card(pos: Vector2, card_size: Vector2, index: int, title_text: String, body_text: String, bg: Color) -> Panel:
	var card := _panel(pos, Vector2(card_size.x, 190.0), bg, 20, Color("e8ddea"), 1)
	var index_label := _label("%02d" % (index + 1), 9, 760, C.muted)
	index_label.position = Vector2(20, 22)
	index_label.size = Vector2(44, 20)
	card.add_child(index_label)
	var title := _label(title_text, 19, 740, C.ink)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.position = Vector2(20, 49)
	title.size = Vector2(card_size.x - 40, 36)
	card.add_child(title)
	var body := _label(body_text, 12, 430, C.muted)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.position = Vector2(20, 91)
	body.size = Vector2(card_size.x - 40, 82)
	body.add_theme_constant_override("line_spacing", 4)
	card.add_child(body)
	return card

func _draw() -> void:
	if _current_route() != "/product":
		super._draw()
		return
	draw_rect(Rect2(Vector2.ZERO, size), C.bg)
	_soft_circle(Vector2(size.x * 0.67, 215), min(size.x * 0.28, 360.0), Color(0.95,0.76,0.86,0.025))
	_soft_circle(Vector2(size.x * 0.58, 575), min(size.x * 0.24, 320.0), Color(0.56,0.49,0.83,0.018))
	var stripe_colors := [C.project, C.runtime, C.editorial, C.evidence, C.valid]
	var stripe_x := 42.0 if _layout == "desktop" else 30.0
	for i in range(18):
		var col: Color = stripe_colors[i % stripe_colors.size()]
		col.a = 0.35
		draw_rect(Rect2(Vector2(stripe_x + i * 17.0, 63.0), Vector2(9.0, 4.0)), col)
