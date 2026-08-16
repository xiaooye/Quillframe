extends "res://scripts/visual_completion.gd"

# Solid is the visual authority. Home and the shared route hero intentionally
# use different breakpoints: Home stacks at 980px while product surfaces stay
# two-column until 900px. Godot's broader `compact` topology spans both ranges,
# so this final layer preserves the compact app shell while matching those
# independent Solid layout and typography contracts.

const SOLID_HOME_STACK_MAX_WIDTH := 980.0
const SOLID_HERO_STACK_MAX_WIDTH := 900.0
const WIDE_COMPACT_H1_SIZE_EN := 48
const WIDE_COMPACT_H1_SIZE_ZH := 46
const NARROW_COMPACT_H1_SIZE := 36

func _build() -> void:
	super._build()
	# Lower geometry layers deliberately preserve desktop/mobile calibrated wraps.
	# Apply the Solid clamp-equivalent tablet type scale last so those lower fixes
	# cannot re-inflate 768px route headings after their stacked layout is built.
	if _layout == "compact" and size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		_polish_narrow_compact_copy()

func _build_compact() -> void:
	if size.x <= SOLID_HOME_STACK_MAX_WIDTH:
		super._build_compact()
		return
	# Home remains copy + launcher columns at 1024px in the Solid authority. Reuse
	# existing Story Loom primitives; only the composition changes at this width.
	var x := 40.0
	var top := 150.0
	var copy_w := 392.0
	var launcher_x := 476.0
	var launcher_w := maxf(size.x - launcher_x - 40.0, 468.0)
	_stage.add_child(_pill("Long-form fiction system · 0.8.x" if _locale == "en-US" else "长篇小说创作系统 · 0.8.x", Vector2(x, top), Vector2(208, 25), Color("f8fbff"), Color("4078a8"), 12, 500, Color("b8d8ee")))
	var title_text := "Let the story\ngrow without\nletting the\nsystem lose\nthe plot." if _locale == "en-US" else "让故事越写越长，\n系统仍然知道\n自己在做什么。"
	var title := _label(title_text, 58 if _locale == "en-US" else 50, 800, C.ink)
	title.position = Vector2(x, top + 32.0)
	title.size = Vector2(copy_w, 300.0)
	title.scale = Vector2.ONE
	title.add_theme_constant_override("line_spacing", -24 if _locale == "en-US" else -11)
	_stage.add_child(title)
	var lede_text := "NovelForge connects creation, context, character knowledge, quality gates, and publication into one inspectable workflow." if _locale == "en-US" else "NovelForge 把创作、上下文、角色知识、质量审查与出版连成一套可检查的工作流。"
	var lede := _label(lede_text, 15, 420, C.muted)
	lede.position = Vector2(x, top + 350.0)
	lede.custom_minimum_size.x = 0.0
	lede.custom_maximum_size = Vector2(copy_w, -1.0)
	lede.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lede.size = Vector2(copy_w, 100.0)
	lede.add_theme_constant_override("line_spacing", 5)
	_stage.add_child(lede)
	var studio := _mixed_text_button("✦ Open Studio" if _locale == "en-US" else "✦ 打开 Studio", Vector2(x, top + 472.0), Vector2(192.0, 54.0), C.runtime, Color.WHITE, 16, 600, 13)
	studio.pressed.connect(_open_external.bind(STUDIO_URL))
	_stage.add_child(studio)
	var knowledge := _text_button("Knowledge" if _locale == "en-US" else "知识库", Vector2(x + 202.0, top + 472.0), Vector2(178.0, 54.0), C.surface_soft, C.runtime, 16, 560, 13)
	knowledge.icon = _books_icon
	knowledge.pressed.connect(_navigate.bind("/docs"))
	_stage.add_child(knowledge)
	_stage.add_child(_trust_pill(Vector2(x, top + 540.0), Vector2(copy_w, 42.0)))
	_build_launcher(Vector2(launcher_x, top + 70.0), Vector2(launcher_w, 410.0))
	_build_lower_sections(top + 690.0, x, size.x - 80.0, false)

func _build_product_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._build_product_compact()
		return
	var page_x := 40.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 112.0
	var hero_h := 570.0
	_build_product_hero(Vector2(page_x, hero_y), Vector2(page_width, hero_h), false)
	var hero := _find_stage_panel(hero_y, 500.0)
	if hero != null:
		var visual_x := hero.size.x * 0.55
		_fit_wide_compact_title(hero, ["NovelForge is a\nfiction production", "NovelForge 是小说生产系统"], visual_x, 28.0)
		_fit_wide_compact_lede(hero, ["It separates creative judgment", "它把创作判断与确定性控制分开"], visual_x, 28.0, 150.0)
	_build_product_cards(Vector2(page_x, hero_y + hero_h + 32.0), page_width, false)

func _patch_studio_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_studio_compact()
		return
	var hero := _find_stage_panel(110.0, 700.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.56
	_fit_wide_compact_title(hero, ["The creative\nworkbench", "把创作放在前台"], visual_x, 28.0)
	_fit_wide_compact_lede(hero, ["Phase 2C now ships", "第二阶段 C"], visual_x, 28.0, 150.0)

func _patch_architecture_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_architecture_compact()
		return
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.59
	_fit_wide_compact_title(hero, ["See how one\nNovelForge run", "看一次 NovelForge"], visual_x, 28.0)
	_fit_wide_compact_lede(hero, ["Project → Manager"], visual_x, 28.0, 115.0)

func _patch_publication_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_publication_compact()
		return
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.47
	_fit_wide_compact_title(hero, ["One accepted\nmanuscript,", "一份已接受稿，"], visual_x, 24.0)
	_fit_wide_compact_title(hero, ["many\ndeterministic", "确定性地产生"], visual_x, 24.0)
	_fit_wide_compact_lede(hero, ["One Publication IR produces", "一份 Publication IR"], visual_x, 24.0, 115.0)

func _patch_inspect_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_inspect_compact()
		return
	var hero := _find_stage_panel(110.0, 400.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.57
	_fit_wide_compact_title(hero, ["Resolve the\nproject before", "任何工具动手之前"], visual_x, 28.0)
	_fit_wide_compact_lede(hero, ["Inspect the manifest", "在浏览器本地检查"], visual_x, 28.0, 125.0)

func _patch_playground_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_playground_compact()
		return
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.59
	_fit_wide_compact_title(hero, ["Make the\nexecution path", "把执行路径变成"], visual_x, 28.0)
	_fit_wide_compact_lede(hero, ["Paste working text", "粘贴工作文本"], visual_x, 28.0, 105.0)

func _patch_agents_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_agents_compact()
		return
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.57
	_fit_wide_compact_title(hero, ["Let your agent\nuse NovelForge", "让 Agent 使用"], visual_x, 28.0)
	_fit_wide_compact_lede(hero, ["The portable Agent Skill", "便携 Agent Skill"], visual_x, 28.0, 125.0)

func _patch_changelog_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_changelog_compact()
		return
	var hero := _find_stage_panel(110.0, 450.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.63
	_fit_wide_compact_title(hero, ["A changelog\nthat separates", "版本记录只写"], visual_x, 28.0)
	_fit_wide_compact_lede(hero, ["NovelForge is pre-1.0", "NovelForge 仍处于"], visual_x, 28.0, 125.0)

func _polish_narrow_compact_copy() -> void:
	match _current_route():
		"/":
			var home_title := _find_label_prefix(self, "Let the story grow")
			if home_title == null:
				home_title = _find_label_prefix(self, "让故事越写越长")
			if home_title != null:
				home_title.text = home_title.text.replace("\n", " ")
				home_title.scale = Vector2.ONE
				home_title.custom_minimum_size.x = 0.0
				home_title.custom_maximum_size = Vector2(size.x - 80.0, -1.0)
				home_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
				home_title.add_theme_font_size_override("font_size", 48 if _locale == "en-US" else 44)
				home_title.add_theme_constant_override("line_spacing", -12 if _locale == "en-US" else -8)
				home_title.size.x = size.x - 80.0
		"/product":
			# Product uses the 112px route origin; all other route heroes use 110px.
			# Using 110 here silently skipped the final wrap pass and left the old
			# desktop-calibrated narrow title box visible at 768px.
			_polish_narrow_surface(["NovelForge\nis a fiction", "NovelForge 是小说"], ["It separates creative judgment", "它把创作判断与确定性控制分开"], 112.0)
		"/studio":
			_polish_narrow_surface(["The creative\nworkbench", "把创作放在前台"], ["Phase 2C now ships", "第二阶段 C"])
		"/architecture":
			_polish_narrow_surface(["See how one\nNovelForge run", "看一次 NovelForge"], ["Project → Manager"])
		"/inspect":
			_polish_narrow_surface(["Resolve the\nproject before", "任何工具动手之前"], ["Inspect the manifest", "在浏览器本地检查"])
		"/playground":
			_polish_narrow_surface(["Make the\nexecution path", "把执行路径变成"], ["Paste working text", "粘贴工作文本"])
		"/agents":
			_polish_narrow_surface(["Let your agent\nuse NovelForge", "让 Agent 使用"], ["The portable Agent Skill", "便携 Agent Skill"])
		"/changelog":
			_polish_narrow_surface(["A changelog\nthat separates", "版本记录只写"], ["NovelForge is pre-1.0", "NovelForge 仍处于"])
		"/publication":
			_polish_narrow_publication()

func _polish_narrow_surface(title_prefixes: Array, lede_prefixes: Array, hero_y: float = 110.0) -> void:
	var hero := _find_stage_panel(hero_y, 400.0)
	if hero == null:
		return
	var title := _find_first_label_prefix(hero, title_prefixes)
	if title == null:
		return
	var available := maxf(hero.size.x - title.position.x - 44.0, 320.0)
	_fit_narrow_compact_label(title, available, NARROW_COMPACT_H1_SIZE, -9)
	var title_height := maxf(title.get_bound_minimum_size().y, 96.0)
	title.size.y = title_height
	var lede := _find_first_label_prefix(hero, lede_prefixes)
	if lede != null:
		lede.position.y = title.position.y + title_height + 22.0
		_fit_narrow_compact_label(lede, available, 15, 4)
		lede.size.y = maxf(lede.get_bound_minimum_size().y, 70.0)

func _polish_narrow_publication() -> void:
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var black := _find_first_label_prefix(hero, ["One accepted", "一份已接受稿"])
	var pink := _find_first_label_prefix(hero, ["many", "确定性地产生"])
	if black == null:
		return
	var available := maxf(hero.size.x - black.position.x - 44.0, 320.0)
	_fit_narrow_compact_label(black, available, NARROW_COMPACT_H1_SIZE, -9)
	var black_height := maxf(black.get_bound_minimum_size().y, 70.0)
	black.size.y = black_height
	if pink != null:
		pink.position = Vector2(black.position.x, black.position.y + black_height - 4.0)
		_fit_narrow_compact_label(pink, available, NARROW_COMPACT_H1_SIZE, -9)
		pink.size.y = maxf(pink.get_bound_minimum_size().y, 70.0)
	var lede := _find_first_label_prefix(hero, ["One Publication IR produces", "一份 Publication IR"])
	if lede != null:
		var title_bottom := black.position.y + black_height
		if pink != null:
			title_bottom = pink.position.y + pink.size.y
		lede.position.y = title_bottom + 20.0
		_fit_narrow_compact_label(lede, available, 15, 4)
		lede.size.y = maxf(lede.get_bound_minimum_size().y, 70.0)

func _fit_narrow_compact_label(label: Label, available: float, font_size: int, line_spacing: int) -> void:
	label.text = label.text.replace("\n", " ")
	label.scale = Vector2.ONE
	label.custom_minimum_size.x = 0.0
	label.custom_maximum_size = Vector2(available, -1.0)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_constant_override("line_spacing", line_spacing)
	label.size.x = available

func _fit_wide_compact_title(hero: Control, prefixes: Array, visual_x: float, gap: float) -> void:
	var title := _find_first_label_prefix(hero, prefixes)
	if title == null:
		return
	var available := maxf(visual_x - title.position.x - gap, 260.0)
	title.text = title.text.replace("\n", " ")
	title.scale = Vector2.ONE
	title.custom_minimum_size.x = 0.0
	title.custom_maximum_size = Vector2(available, -1.0)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_font_size_override("font_size", WIDE_COMPACT_H1_SIZE_EN if _locale == "en-US" else WIDE_COMPACT_H1_SIZE_ZH)
	title.add_theme_constant_override("line_spacing", -17 if _locale == "en-US" else -7)
	title.size.x = available

func _fit_wide_compact_lede(hero: Control, prefixes: Array, visual_x: float, gap: float, min_height: float) -> void:
	var lede := _find_first_label_prefix(hero, prefixes)
	if lede == null:
		return
	var available := maxf(visual_x - lede.position.x - gap, 260.0)
	lede.text = lede.text.replace("\n", " ")
	lede.custom_minimum_size.x = 0.0
	lede.custom_maximum_size = Vector2(available, -1.0)
	lede.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lede.size.x = available
	lede.size.y = maxf(lede.size.y, min_height)
	lede.add_theme_constant_override("line_spacing", 4 if _locale == "en-US" else 5)

func _find_first_label_prefix(parent: Node, prefixes: Array) -> Label:
	for prefix in prefixes:
		var label := _find_label_prefix(parent, str(prefix))
		if label != null:
			return label
	return null
