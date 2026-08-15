extends Control

const Story = preload("res://generated/story_loom_tokens.gd")
const SystemMap = preload("res://scripts/system_map.gd")
const AmbientBackdrop = preload("res://scripts/ambient_backdrop.gd")

const NAV_ITEMS := [
	["PRODUCT", "/product"],
	["STUDIO", "/studio"],
	["ARCHITECTURE", "/architecture"],
	["PUBLICATION", "/publication"],
]

const PAGE_DATA := {
	"/": {
		"eyebrow": "PRODUCT EXPERIENCE",
		"title": "Weave boldly. Settle carefully. Publish exactly.",
		"copy": "NovelForge keeps long-form fiction production coherent across Project state, sparse Context, Manager / Worker execution, typed Gates, Settlement, and deterministic Publication — without pretending the UI is authority.",
		"primary": ["OPEN PRODUCT", "/product"],
		"secondary": ["EXPLORE ARCHITECTURE", "/architecture"],
	},
	"/start": {
		"eyebrow": "PRODUCT EXPERIENCE",
		"title": "Weave boldly. Settle carefully. Publish exactly.",
		"copy": "NovelForge keeps long-form fiction production coherent across Project state, sparse Context, Manager / Worker execution, typed Gates, Settlement, and deterministic Publication — without pretending the UI is authority.",
		"primary": ["OPEN PRODUCT", "/product"],
		"secondary": ["EXPLORE ARCHITECTURE", "/architecture"],
	},
	"/product": {
		"eyebrow": "PRODUCT / STORY LOOM",
		"title": "One creative workspace, explicit authority boundaries.",
		"copy": "Project, Runtime, Editorial, Evidence, and Validated state stay visually distinct while sharing one coherent fiction-production workspace.",
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["EXPLORE ARCHITECTURE", "/architecture"],
	},
	"/studio": {
		"eyebrow": "STUDIO / PRODUCTION",
		"title": "Shape the run without losing the thread.",
		"copy": "Sparse context enters execution, candidates move through typed gates, and accepted changes remain visibly downstream of verification and settlement.",
		"primary": ["INSPECT RUNTIME", "/inspect"],
		"secondary": ["VIEW AGENTS", "/agents"],
	},
	"/architecture": {
		"eyebrow": "ARCHITECTURE / STORY LOOM",
		"title": "See one run move through the whole system.",
		"copy": "Project -> Manager -> Context -> Worker -> Gate -> Settlement -> Publication. Each node keeps its own mechanism boundary while the product stays visually coherent.",
		"primary": ["OPEN PLAYGROUND", "/playground"],
		"secondary": ["INSPECT STATE", "/inspect"],
	},
	"/publication": {
		"eyebrow": "PUBLICATION / DERIVED OUTPUT",
		"title": "One accepted manuscript, many exact derivatives.",
		"copy": "TXT, Web, Print, and EPUB remain presentation layers over accepted manuscript truth, with provenance kept visible and authority=false.",
		"primary": ["INSPECT SOURCE", "/inspect"],
		"secondary": ["VIEW ARCHITECTURE", "/architecture"],
	},
	"/inspect": {
		"eyebrow": "INSPECT / EVIDENCE",
		"title": "Read exact state without claiming mutation authority.",
		"copy": "Inspect fingerprints, handoffs, receipts, and runtime evidence as projections of current state rather than a second source of truth.",
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["VIEW ARCHITECTURE", "/architecture"],
	},
	"/playground": {
		"eyebrow": "PLAYGROUND / LOCAL EXPERIMENT",
		"title": "Try the machinery without touching accepted state.",
		"copy": "Deterministic previews and local experiments stay visually distinct from production state, so exploration never masquerades as settlement.",
		"primary": ["VIEW ARCHITECTURE", "/architecture"],
		"secondary": ["OPEN STUDIO", "/studio"],
	},
	"/agents": {
		"eyebrow": "AGENTS / EXECUTION",
		"title": "Specialized participants, one observable run.",
		"copy": "Manager, workers, gates, and handoffs appear as coordinated execution roles instead of being flattened into one chat-shaped abstraction.",
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["INSPECT STATE", "/inspect"],
	},
	"/changelog": {
		"eyebrow": "CHANGELOG / PRODUCT EVOLUTION",
		"title": "Keep the product playful without losing contract truth.",
		"copy": "Product evolution stays visible while documentation remains a separate semantic web surface and runtime authority remains unchanged.",
		"primary": ["BACK TO PRODUCT", "/"],
		"secondary": ["VIEW ARCHITECTURE", "/architecture"],
	},
}

const ROUTE_SELECTION := {
	"/":"project","/start":"project","/product":"project","/studio":"worker",
	"/architecture":"manager","/publication":"publication","/inspect":"inspector",
	"/playground":"context","/agents":"agents","/changelog":"project",
}

const ROUTE_ACCENTS := {
	"/": Story.EDITORIAL, "/start": Story.EDITORIAL, "/product": Story.PROJECT,
	"/studio": Story.RUNTIME, "/architecture": Story.RUNTIME, "/publication": Story.EDITORIAL,
	"/inspect": Story.EVIDENCE, "/playground": Story.EDITORIAL, "/agents": Story.VALIDATED,
	"/changelog": Story.MUTED_FOREGROUND,
}

var _current_route := "/"
var _accent := Story.EDITORIAL
var _layout_mode := "desktop"
var _nav_buttons: Dictionary = {}
var _map
var _backdrop
var _docs_button: Button
var _hero_grid: GridContainer
var _hero_copy: MarginContainer
var _hero_visual: PanelContainer
var _action_grid: GridContainer
var _loom_grid: GridContainer
var _stats_grid: GridContainer
var _cards_grid: GridContainer
var _page_margin: MarginContainer
var _topbar: PanelContainer
var _brand_meta: Label
var _search_button: Button
var _studio_button: Button
var _eyebrow: Label
var _title: Label
var _copy: Label
var _primary_button: Button
var _secondary_button: Button
var _primary_target := "/product"
var _secondary_target := "/architecture"

func _ready() -> void:
	_build_interface()
	_navigate(_browser_path(), false)
	_install_browser_history_guard()
	resized.connect(_apply_responsive_layout)
	call_deferred("_apply_responsive_layout")
	call_deferred("_signal_web_ready")

func _build_interface() -> void:
	_backdrop = AmbientBackdrop.new()
	_backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_backdrop)

	var shell := VBoxContainer.new()
	shell.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shell.add_theme_constant_override("separation", 0)
	add_child(shell)

	_topbar = _build_topbar()
	shell.add_child(_topbar)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	shell.add_child(scroll)

	_page_margin = MarginContainer.new()
	_page_margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_set_page_margins(28)
	scroll.add_child(_page_margin)

	var page := VBoxContainer.new()
	page.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	page.add_theme_constant_override("separation", 22)
	_page_margin.add_child(page)

	_hero_grid = GridContainer.new()
	_hero_grid.columns = 2
	_hero_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_hero_grid.add_theme_constant_override("h_separation", 28)
	_hero_grid.add_theme_constant_override("v_separation", 20)
	page.add_child(_hero_grid)
	_hero_copy = _build_hero_copy()
	_hero_grid.add_child(_hero_copy)
	_hero_visual = _build_hero_visual()
	_hero_grid.add_child(_hero_visual)

	_loom_grid = _build_story_loom_strip()
	page.add_child(_loom_grid)
	_stats_grid = _build_stats()
	page.add_child(_stats_grid)
	_cards_grid = _build_capability_cards()
	page.add_child(_cards_grid)
	page.add_child(_build_footer_note())

func _build_topbar() -> PanelContainer:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.y = 64
	panel.add_theme_stylebox_override("panel", _style(Color(1,1,1,0.94), Color(Story.BORDER.r,Story.BORDER.g,Story.BORDER.b,0.72), 0, 1))
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 24)
	margin.add_theme_constant_override("margin_right", 24)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	panel.add_child(margin)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	margin.add_child(row)

	var brand := HBoxContainer.new()
	brand.custom_minimum_size.x = 210
	brand.add_theme_constant_override("separation", 9)
	row.add_child(brand)
	var mark := PanelContainer.new()
	mark.custom_minimum_size = Vector2(38,38)
	mark.add_theme_stylebox_override("panel", _style(Story.EDITORIAL_FILL, Color(Story.EDITORIAL.r,Story.EDITORIAL.g,Story.EDITORIAL.b,0.34), 13, 1))
	brand.add_child(mark)
	var mark_label := Label.new()
	mark_label.text = "N"
	mark_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mark_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	mark_label.add_theme_font_size_override("font_size", 16)
	mark_label.add_theme_color_override("font_color", Story.EDITORIAL)
	mark.add_child(mark_label)
	var brand_title := Label.new()
	brand_title.text = "NovelForge"
	brand_title.add_theme_font_size_override("font_size", 17)
	brand_title.add_theme_color_override("font_color", Story.FOREGROUND)
	brand.add_child(brand_title)
	_brand_meta = Label.new()
	_brand_meta.text = "0.8.x"
	_brand_meta.add_theme_font_size_override("font_size", 9)
	_brand_meta.add_theme_color_override("font_color", Story.RUNTIME)
	brand.add_child(_brand_meta)

	var nav_scroll := ScrollContainer.new()
	nav_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	nav_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	row.add_child(nav_scroll)
	var nav := HBoxContainer.new()
	nav.add_theme_constant_override("separation", 2)
	nav_scroll.add_child(nav)
	for item in NAV_ITEMS:
		var label := str(item[0])
		var route := str(item[1])
		var button := Button.new()
		button.text = label
		button.flat = true
		button.custom_minimum_size = Vector2(96, 42)
		button.add_theme_font_size_override("font_size", 10)
		button.add_theme_color_override("font_color", Story.MUTED_FOREGROUND)
		button.add_theme_color_override("font_hover_color", Story.FOREGROUND)
		button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
		button.pressed.connect(func(): _navigate(route, true))
		nav.add_child(button)
		_nav_buttons[route] = button

	_docs_button = Button.new()
	_docs_button.text = "DOCS"
	_docs_button.flat = true
	_docs_button.custom_minimum_size = Vector2(72,42)
	_docs_button.add_theme_font_size_override("font_size", 10)
	_docs_button.add_theme_color_override("font_color", Story.MUTED_FOREGROUND)
	_docs_button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_docs_button.pressed.connect(_open_docs)
	nav.add_child(_docs_button)

	_search_button = Button.new()
	_search_button.text = "Search NovelForge"
	_search_button.custom_minimum_size = Vector2(176, 40)
	_search_button.add_theme_font_size_override("font_size", 9)
	_search_button.add_theme_color_override("font_color", Story.MUTED_FOREGROUND)
	_search_button.add_theme_stylebox_override("normal", _style(Color(1,1,1,0.76), Story.BORDER, 12, 1))
	_search_button.add_theme_stylebox_override("hover", _style(Story.PROJECT_FILL, Story.PROJECT, 12, 1))
	_search_button.pressed.connect(_open_docs)
	row.add_child(_search_button)

	_studio_button = Button.new()
	_studio_button.text = "OPEN STUDIO"
	_studio_button.custom_minimum_size = Vector2(132,40)
	_studio_button.add_theme_font_size_override("font_size", 9)
	_studio_button.add_theme_color_override("font_color", Color.WHITE)
	_studio_button.add_theme_stylebox_override("normal", _style(Story.RUNTIME, Story.RUNTIME, 14, 0))
	_studio_button.add_theme_stylebox_override("hover", _style(Story.RUNTIME.lightened(0.08), Story.RUNTIME, 14, 0))
	_studio_button.pressed.connect(_open_hosted_studio)
	row.add_child(_studio_button)
	return panel

func _build_hero_copy() -> MarginContainer:
	var panel := MarginContainer.new()
	panel.custom_minimum_size = Vector2(520, 470)
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.add_theme_constant_override("margin_left", 26)
	panel.add_theme_constant_override("margin_right", 20)
	panel.add_theme_constant_override("margin_top", 44)
	panel.add_theme_constant_override("margin_bottom", 26)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	panel.add_child(column)

	var badges := HBoxContainer.new()
	badges.add_theme_constant_override("separation", 8)
	column.add_child(badges)
	badges.add_child(_badge("local-first", Story.EDITORIAL_FILL, Story.EDITORIAL))
	badges.add_child(_badge("authority-aware", Story.NEUTRAL_FILL, Story.MUTED_FOREGROUND))

	_eyebrow = Label.new()
	_eyebrow.text = "PRODUCT EXPERIENCE"
	_eyebrow.add_theme_font_size_override("font_size", 9)
	_eyebrow.add_theme_color_override("font_color", Story.EDITORIAL)
	column.add_child(_eyebrow)

	_title = Label.new()
	_title.text = "Weave boldly. Settle carefully. Publish exactly."
	_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_title.add_theme_font_size_override("font_size", 46)
	_title.add_theme_color_override("font_color", Story.FOREGROUND)
	column.add_child(_title)

	_copy = Label.new()
	_copy.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_copy.add_theme_font_size_override("font_size", 13)
	_copy.add_theme_color_override("font_color", Story.MUTED_FOREGROUND)
	_copy.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(_copy)

	_action_grid = GridContainer.new()
	_action_grid.columns = 2
	_action_grid.add_theme_constant_override("h_separation", 10)
	_action_grid.add_theme_constant_override("v_separation", 8)
	column.add_child(_action_grid)
	_primary_button = Button.new()
	_primary_button.custom_minimum_size = Vector2(168, 46)
	_primary_button.add_theme_font_size_override("font_size", 10)
	_primary_button.add_theme_color_override("font_color", Color.WHITE)
	_primary_button.pressed.connect(func(): _navigate(_primary_target, true))
	_action_grid.add_child(_primary_button)
	_secondary_button = Button.new()
	_secondary_button.custom_minimum_size = Vector2(190, 46)
	_secondary_button.add_theme_font_size_override("font_size", 10)
	_secondary_button.add_theme_color_override("font_color", Story.FOREGROUND)
	_secondary_button.add_theme_stylebox_override("normal", _style(Color(1,1,1,0.70), Story.BORDER, 12, 1))
	_secondary_button.add_theme_stylebox_override("hover", _style(Story.RUNTIME_FILL, Story.RUNTIME, 12, 1))
	_secondary_button.pressed.connect(func(): _navigate(_secondary_target, true))
	_action_grid.add_child(_secondary_button)

	var release := Label.new()
	release.text = "Latest  0.8.x   ·   core >=0.8,<0.9   ·   Updated Jul 28, 2026"
	release.add_theme_font_size_override("font_size", 9)
	release.add_theme_color_override("font_color", Story.NEUTRAL)
	column.add_child(release)
	return panel

func _build_hero_visual() -> PanelContainer:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(620, 500)
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.add_theme_stylebox_override("panel", _style(Color("#FFF3F8"), Color(Story.EDITORIAL.r, Story.EDITORIAL.g, Story.EDITORIAL.b, 0.16), 34, 1))
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 26)
	margin.add_theme_constant_override("margin_right", 26)
	margin.add_theme_constant_override("margin_top", 24)
	margin.add_theme_constant_override("margin_bottom", 24)
	panel.add_child(margin)
	_map = SystemMap.new()
	_map.custom_minimum_size = Vector2(520, 450)
	_map.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_map.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_map.node_selected.connect(_on_map_node_selected)
	margin.add_child(_map)
	return panel

func _build_story_loom_strip() -> GridContainer:
	var grid := GridContainer.new()
	grid.columns = 5
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 0)
	grid.add_theme_constant_override("v_separation", 8)
	var lanes := [
		["P", "PROJECT", "context + state", Story.PROJECT_FILL, Story.PROJECT],
		["R", "RUNTIME", "manager + worker", Story.RUNTIME_FILL, Story.RUNTIME],
		["E", "EDITORIAL", "voice + scene", Story.EDITORIAL_FILL, Story.EDITORIAL],
		["K", "EVIDENCE", "gates + lineage", Story.EVIDENCE_FILL, Story.EVIDENCE],
		["V", "VALIDATED", "accepted + publish", Story.VALIDATED_FILL, Story.VALIDATED],
	]
	for lane in lanes:
		var card := PanelContainer.new()
		card.custom_minimum_size.y = 70
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.add_theme_stylebox_override("panel", _style(lane[3], Color(lane[4].r,lane[4].g,lane[4].b,0.18), 0, 1))
		grid.add_child(card)
		var margin := MarginContainer.new()
		margin.add_theme_constant_override("margin_left", 18)
		margin.add_theme_constant_override("margin_right", 18)
		card.add_child(margin)
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		margin.add_child(row)
		var icon := Label.new()
		icon.text = str(lane[0])
		icon.add_theme_font_size_override("font_size", 13)
		icon.add_theme_color_override("font_color", lane[4])
		row.add_child(icon)
		var copy := VBoxContainer.new()
		copy.add_theme_constant_override("separation", -1)
		row.add_child(copy)
		var title := Label.new()
		title.text = str(lane[1])
		title.add_theme_font_size_override("font_size", 10)
		title.add_theme_color_override("font_color", lane[4])
		copy.add_child(title)
		var sub := Label.new()
		sub.text = str(lane[2])
		sub.add_theme_font_size_override("font_size", 9)
		sub.add_theme_color_override("font_color", Story.MUTED_FOREGROUND)
		copy.add_child(sub)
	return grid

func _build_stats() -> GridContainer:
	var grid := GridContainer.new()
	grid.columns = 3
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 0)
	grid.add_theme_constant_override("v_separation", 6)
	for item in [["One run", "Context to Settlement"], ["Zero poll", "Event-driven UI"], ["Typed", "Manager · Worker · Gate"]]:
		var card := PanelContainer.new()
		card.custom_minimum_size.y = 74
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.add_theme_stylebox_override("panel", _style(Color(1,1,1,0.55), Color(Story.BORDER.r,Story.BORDER.g,Story.BORDER.b,0.50), 0, 0))
		grid.add_child(card)
		var margin := MarginContainer.new()
		margin.add_theme_constant_override("margin_left", 24)
		margin.add_theme_constant_override("margin_right", 24)
		card.add_child(margin)
		var row := HBoxContainer.new()
		margin.add_child(row)
		var strong := Label.new()
		strong.text = str(item[0])
		strong.add_theme_font_size_override("font_size", 18)
		strong.add_theme_color_override("font_color", Story.FOREGROUND)
		row.add_child(strong)
		var spacer := Control.new()
		spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(spacer)
		var sub := Label.new()
		sub.text = str(item[1])
		sub.add_theme_font_size_override("font_size", 9)
		sub.add_theme_color_override("font_color", Story.MUTED_FOREGROUND)
		row.add_child(sub)
	return grid

func _build_capability_cards() -> GridContainer:
	var grid := GridContainer.new()
	grid.columns = 4
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 12)
	var cards := [
		["Project truth", "Pinned identity, framework lock, and attestation remain explicit.", Story.PROJECT_FILL, Story.PROJECT],
		["Sparse context", "Load only the support a run needs, with exclusions still visible.", Story.EVIDENCE_FILL, Story.EVIDENCE],
		["Typed execution", "Manager, worker, and gate boundaries stay inspectable.", Story.RUNTIME_FILL, Story.RUNTIME],
		["Exact publication", "Derived artifacts remain downstream of accepted manuscript state.", Story.VALIDATED_FILL, Story.VALIDATED],
	]
	for item in cards:
		var card := PanelContainer.new()
		card.custom_minimum_size = Vector2(240, 150)
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.add_theme_stylebox_override("panel", _style(item[2], Color(item[3].r,item[3].g,item[3].b,0.18), 20, 1))
		grid.add_child(card)
		var margin := MarginContainer.new()
		margin.add_theme_constant_override("margin_left", 20)
		margin.add_theme_constant_override("margin_right", 20)
		margin.add_theme_constant_override("margin_top", 18)
		margin.add_theme_constant_override("margin_bottom", 18)
		card.add_child(margin)
		var col := VBoxContainer.new()
		col.add_theme_constant_override("separation", 10)
		margin.add_child(col)
		var spark := Label.new()
		spark.text = "+"
		spark.add_theme_font_size_override("font_size", 18)
		spark.add_theme_color_override("font_color", item[3])
		col.add_child(spark)
		var title := Label.new()
		title.text = str(item[0])
		title.add_theme_font_size_override("font_size", 15)
		title.add_theme_color_override("font_color", Story.FOREGROUND)
		col.add_child(title)
		var desc := Label.new()
		desc.text = str(item[1])
		desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		desc.add_theme_font_size_override("font_size", 10)
		desc.add_theme_color_override("font_color", Story.MUTED_FOREGROUND)
		col.add_child(desc)
	return grid

func _build_footer_note() -> Control:
	var note := Label.new()
	note.text = "NovelForge · Story Loom · Godot Web runtime · Documentation remains web-native"
	note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	note.add_theme_font_size_override("font_size", 9)
	note.add_theme_color_override("font_color", Story.NEUTRAL)
	note.custom_minimum_size.y = 56
	return note

func _badge(text: String, bg: Color, fg: Color) -> PanelContainer:
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _style(bg, Color(fg.r,fg.g,fg.b,0.28), 12, 1))
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_top", 5)
	margin.add_theme_constant_override("margin_bottom", 5)
	panel.add_child(margin)
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", 9)
	label.add_theme_color_override("font_color", fg)
	margin.add_child(label)
	return panel

func _navigate(path: String, push_history: bool = true) -> void:
	var route := _normalize_route(path)
	if not PAGE_DATA.has(route): route = "/"
	_current_route = route
	_accent = ROUTE_ACCENTS.get(route, Story.EDITORIAL)
	var data: Dictionary = PAGE_DATA[route]
	_eyebrow.text = str(data["eyebrow"])
	_eyebrow.add_theme_color_override("font_color", _accent)
	_title.text = str(data["title"])
	_copy.text = str(data["copy"])
	var primary: Array = data["primary"]
	var secondary: Array = data["secondary"]
	_primary_button.text = str(primary[0])
	_primary_target = str(primary[1])
	_secondary_button.text = str(secondary[0])
	_secondary_target = str(secondary[1])
	_primary_button.add_theme_stylebox_override("normal", _style(_accent, _accent, 12, 0))
	_primary_button.add_theme_stylebox_override("hover", _style(_accent.lightened(0.08), _accent, 12, 0))
	for route_key in _nav_buttons:
		var button: Button = _nav_buttons[route_key]
		var active := str(route_key) == route or (route == "/" and str(route_key) == "/product")
		button.add_theme_color_override("font_color", _accent if active else Story.MUTED_FOREGROUND)
		button.add_theme_stylebox_override("normal", _style(Color(_accent.r,_accent.g,_accent.b,0.08) if active else Color(0,0,0,0), Color(0,0,0,0), 10, 0))
	_map.set_focus(route)
	var selected := str(ROUTE_SELECTION.get(route, "project"))
	_map.select_node(selected)
	_backdrop.set_accent(_accent)
	if push_history and OS.has_feature("web"):
		JavaScriptBridge.eval("window.history.pushState({}, '', '%s');" % route)

func _on_map_node_selected(node_id: String) -> void:
	match node_id:
		"project": _navigate("/product", true)
		"manager": _navigate("/architecture", true)
		"context": _navigate("/playground", true)
		"worker": _navigate("/studio", true)
		"agents": _navigate("/agents", true)
		"inspector": _navigate("/inspect", true)
		"publication": _navigate("/publication", true)
		_: pass

func _responsive_width() -> float:
	if OS.has_feature("web"):
		return float(JavaScriptBridge.eval("window.innerWidth"))
	return size.x

func _responsive_height() -> float:
	if OS.has_feature("web"):
		return float(JavaScriptBridge.eval("window.innerHeight"))
	return size.y

func _apply_responsive_layout() -> void:
	var viewport_width := _responsive_width()
	var viewport_height := _responsive_height()
	var phone := viewport_width < 720.0
	var compact := viewport_width < 1120.0
	_layout_mode = "phone" if phone else ("compact" if compact else "desktop")
	_hero_grid.columns = 1 if compact else 2
	_action_grid.columns = 1 if phone else 2
	_loom_grid.columns = 1 if phone else (2 if compact else 5)
	_stats_grid.columns = 1 if phone else 3
	_cards_grid.columns = 1 if phone else (2 if compact else 4)
	_search_button.visible = not compact
	_studio_button.visible = not phone
	_brand_meta.visible = not phone
	if phone:
		_topbar.custom_minimum_size.y = 58
		_hero_copy.custom_minimum_size = Vector2(0, 0)
		_hero_visual.custom_minimum_size = Vector2(0, maxf(360.0, viewport_height * 0.54))
		_map.custom_minimum_size = Vector2(0, 340)
		_title.add_theme_font_size_override("font_size", 34)
		_set_page_margins(12)
	elif compact:
		_topbar.custom_minimum_size.y = 62
		_hero_copy.custom_minimum_size = Vector2(0, 0)
		_hero_visual.custom_minimum_size = Vector2(0, 430)
		_map.custom_minimum_size = Vector2(0, 380)
		_title.add_theme_font_size_override("font_size", 42)
		_set_page_margins(20)
	else:
		_topbar.custom_minimum_size.y = 64
		_hero_copy.custom_minimum_size = Vector2(520, 470)
		_hero_visual.custom_minimum_size = Vector2(620, 500)
		_map.custom_minimum_size = Vector2(520, 450)
		_title.add_theme_font_size_override("font_size", 46)
		_set_page_margins(28)
	_map.set_layout_mode(_layout_mode)
	_publish_layout_state()

func _set_page_margins(value: int) -> void:
	_page_margin.add_theme_constant_override("margin_left", value)
	_page_margin.add_theme_constant_override("margin_right", value)
	_page_margin.add_theme_constant_override("margin_top", value)
	_page_margin.add_theme_constant_override("margin_bottom", value)

func _publish_layout_state() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("document.documentElement.dataset.novelforgeLayout='%s';" % _layout_mode)

func _install_browser_history_guard() -> void:
	if not OS.has_feature("web"): return
	JavaScriptBridge.eval("if(!window.__novelforgePopstateReloadInstalled){window.__novelforgePopstateReloadInstalled=true;window.addEventListener('popstate',()=>window.location.reload());}")

func _browser_path() -> String:
	if not OS.has_feature("web"): return "/"
	return str(JavaScriptBridge.eval("window.location.pathname"))

func _signal_web_ready() -> void:
	_apply_responsive_layout()
	if not OS.has_feature("web"): return
	JavaScriptBridge.eval("document.documentElement.dataset.novelforgeRuntime='ready';const loader=document.getElementById('nf-loader');if(loader){loader.classList.add('is-ready');}window.dispatchEvent(new CustomEvent('novelforge:ready')); ")

func _open_docs() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.location.assign('/docs');")

func _open_hosted_studio() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.open('https://studio.novelforge.wei-dev.com','_blank','noopener,noreferrer');")
	else:
		_navigate("/studio", true)

func _normalize_route(path: String) -> String:
	var clean := path.split("?", false, 1)[0]
	if clean.length() > 1: clean = clean.trim_suffix("/")
	return clean if not clean.is_empty() else "/"

func _style(bg: Color, border: Color, radius: int, border_width: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.border_width_left = border_width
	style.border_width_right = border_width
	style.border_width_top = border_width
	style.border_width_bottom = border_width
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	return style
