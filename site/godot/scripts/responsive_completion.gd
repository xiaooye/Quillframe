extends "res://scripts/wide_compact_parity.gd"

# Final responsive topology alignment against the active Solid product CSS.
# The app shell collapses desktop navigation at 980px, while Product proof cards
# use two columns through 1120px and one column at 760px and below. These
# content-driven breakpoints are independent from Godot's coarse topology names.
const SOLID_SHELL_COMPACT_MAX_WIDTH := 980.0
const SOLID_CARD_TWO_COLUMN_MAX_WIDTH := 1120.0
const SOLID_CARD_SINGLE_COLUMN_MAX_WIDTH := 760.0

func _build_header() -> void:
	super._build_header()
	if _layout != "compact" or size.x > SOLID_SHELL_COMPACT_MAX_WIDTH:
		return
	if get_child_count() == 0:
		return
	var header := get_child(get_child_count() - 1)
	if not header is Panel:
		return

	# Solid hides desktop navigation at <=980px but preserves language, appearance,
	# and menu access. Remove only the desktop route buttons; keep brand/version.
	for child in header.get_children():
		if child is Button and str((child as Button).text) in ["Product", "Studio", "Architecture", "Publication", "Docs"]:
			header.remove_child(child)
			child.free()

	var header_width := header.size.x
	var lang := _text_button("中文" if _locale == "en-US" else "EN", Vector2(header_width - 166.0, 5.0), Vector2(66.0, 44.0), Color(0,0,0,0), C.runtime, 13, 620, 10)
	lang.pressed.connect(_toggle_locale)
	header.add_child(lang)
	var theme := _text_button("☼" if _dark else "◐", Vector2(header_width - 94.0, 5.0), Vector2(44.0, 44.0), Color(0,0,0,0), C.runtime, 16, 650, 10)
	theme.add_theme_font_override("font", _mixed_font(650))
	theme.pressed.connect(_toggle_appearance)
	header.add_child(theme)
	var menu := _text_button("≡", Vector2(header_width - 46.0, 5.0), Vector2(44.0, 44.0), Color(0,0,0,0), C.runtime, 17, 700, 10)
	menu.pressed.connect(_toggle_mobile_menu)
	header.add_child(menu)

func _build_product_compact() -> void:
	var page_x := 40.0
	var page_width := size.x - page_x * 2.0
	var hero_y := 112.0
	var stacked := size.x <= SOLID_HERO_STACK_MAX_WIDTH
	var hero_h := 720.0 if stacked else 570.0
	_build_product_hero(Vector2(page_x, hero_y), Vector2(page_width, hero_h), stacked)

	# Wide compact keeps the Solid two-column hero and needs the same Godot text
	# width compensation already proven in the preceding completion layer.
	if not stacked:
		var hero := _find_stage_panel(hero_y, 500.0)
		if hero != null:
			var visual_x := hero.size.x * 0.55
			_fit_wide_compact_title(hero, ["NovelForge is a\nfiction production", "NovelForge 是小说生产系统"], visual_x, 28.0)
			_fit_wide_compact_lede(hero, ["It separates creative judgment", "它把创作判断与确定性控制分开"], visual_x, 28.0, 150.0)

	_build_product_cards_adaptive(Vector2(page_x, hero_y + hero_h + 28.0), page_width)

func _build_product_cards_adaptive(pos: Vector2, width: float) -> void:
	var cards = PRODUCT_CARDS_ZH if _locale == "zh-CN" else PRODUCT_CARDS_EN
	var fills := [Color("fffafd"), Color("fffaf9"), Color("fbfdfb"), Color("fffdf9")]
	if size.x <= SOLID_CARD_SINGLE_COLUMN_MAX_WIDTH:
		var y := pos.y
		for i in range(cards.size()):
			_stage.add_child(_product_card(Vector2(pos.x, y), Vector2(width, 190.0), i, str(cards[i][0]), str(cards[i][1]), fills[i]))
			y += 204.0
		_stage.custom_minimum_size.y = maxf(_stage.custom_minimum_size.y, y + 36.0)
		return

	# Solid .unified-card-grid is two columns at <=1120px. Product compact always
	# falls inside that range, but keep the authority explicit for future topology
	# changes rather than coupling it to the word `compact`.
	if size.x <= SOLID_CARD_TWO_COLUMN_MAX_WIDTH:
		var gap := 13.0
		var card_w := (width - gap) / 2.0
		for i in range(cards.size()):
			var row := i / 2
			var col := i % 2
			var card_pos := Vector2(pos.x + col * (card_w + gap), pos.y + row * 204.0)
			_stage.add_child(_product_card(card_pos, Vector2(card_w, 190.0), i, str(cards[i][0]), str(cards[i][1]), fills[i]))
		return

	_build_product_cards(pos, width, false)
