extends "res://scripts/visual_completion.gd"

# Solid is the visual authority for product surfaces. Its shared
# .product-surface-hero remains two-column above 900px and stacks only at
# max-width: 900px. Godot's broader `compact` topology spans both 1024 and 768,
# so preserve the compact header while matching Solid's independent hero
# breakpoint: wide compact keeps two columns; narrow compact reuses the stacked
# geometry from geometry_parity.gd.

const SOLID_HERO_STACK_MAX_WIDTH := 900.0
const WIDE_COMPACT_H1_SIZE_EN := 48
const WIDE_COMPACT_H1_SIZE_ZH := 46

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
	_fit_wide_compact_title(
		hero,
		["The creative\nworkbench", "把创作放在前台"],
		visual_x,
		28.0
	)
	_fit_wide_compact_lede(hero, ["Phase 2C now ships", "第二阶段 C"], visual_x, 28.0, 150.0)

func _patch_architecture_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_architecture_compact()
		return
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.59
	_fit_wide_compact_title(
		hero,
		["See how one\nNovelForge run", "看一次 NovelForge"],
		visual_x,
		28.0
	)
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
	_fit_wide_compact_title(
		hero,
		["Resolve the\nproject before", "任何工具动手之前"],
		visual_x,
		28.0
	)
	_fit_wide_compact_lede(hero, ["Inspect the manifest", "在浏览器本地检查"], visual_x, 28.0, 125.0)

func _patch_playground_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_playground_compact()
		return
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.59
	_fit_wide_compact_title(
		hero,
		["Make the\nexecution path", "把执行路径变成"],
		visual_x,
		28.0
	)
	_fit_wide_compact_lede(hero, ["Paste working text", "粘贴工作文本"], visual_x, 28.0, 105.0)

func _patch_agents_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_agents_compact()
		if _locale == "zh-CN":
			var hero_narrow := _find_stage_panel(110.0, 700.0)
			if hero_narrow != null:
				var title_narrow := _find_label_prefix(hero_narrow, "让 Agent 使用")
				if title_narrow != null:
					title_narrow.add_theme_font_size_override("font_size", 44)
					title_narrow.add_theme_constant_override("line_spacing", -10)
					title_narrow.size.y = minf(title_narrow.size.y, 230.0)
		return
	var hero := _find_stage_panel(110.0, 500.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.57
	_fit_wide_compact_title(
		hero,
		["Let your agent\nuse NovelForge", "让 Agent 使用"],
		visual_x,
		28.0
	)
	_fit_wide_compact_lede(hero, ["The portable Agent Skill", "便携 Agent Skill"], visual_x, 28.0, 125.0)

func _patch_changelog_compact() -> void:
	if size.x <= SOLID_HERO_STACK_MAX_WIDTH:
		super._patch_changelog_compact()
		return
	var hero := _find_stage_panel(110.0, 450.0)
	if hero == null:
		return
	var visual_x := hero.size.x * 0.63
	_fit_wide_compact_title(
		hero,
		["A changelog\nthat separates", "版本记录只写"],
		visual_x,
		28.0
	)
	_fit_wide_compact_lede(hero, ["NovelForge is pre-1.0", "NovelForge 仍处于"], visual_x, 28.0, 125.0)

func _fit_wide_compact_title(hero: Control, prefixes: Array, visual_x: float, gap: float) -> void:
	var title := _find_first_label_prefix(hero, prefixes)
	if title == null:
		return
	var available := maxf(visual_x - title.position.x - gap, 260.0)
	title.size.x = minf(title.size.x, available)
	title.scale = Vector2.ONE
	title.add_theme_font_size_override("font_size", WIDE_COMPACT_H1_SIZE_EN if _locale == "en-US" else WIDE_COMPACT_H1_SIZE_ZH)
	title.add_theme_constant_override("line_spacing", -17 if _locale == "en-US" else -7)

func _fit_wide_compact_lede(hero: Control, prefixes: Array, visual_x: float, gap: float, min_height: float) -> void:
	var lede := _find_first_label_prefix(hero, prefixes)
	if lede == null:
		return
	var available := maxf(visual_x - lede.position.x - gap, 260.0)
	lede.text = lede.text.replace("\n", " ")
	lede.size.x = minf(lede.size.x, available)
	lede.size.y = maxf(lede.size.y, min_height)
	lede.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lede.add_theme_constant_override("line_spacing", 4 if _locale == "en-US" else 5)

func _find_first_label_prefix(parent: Node, prefixes: Array) -> Label:
	for prefix in prefixes:
		var label := _find_label_prefix(parent, str(prefix))
		if label != null:
			return label
	return null
