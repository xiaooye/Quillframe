extends Control

const SystemMap = preload("res://scripts/system_map.gd")

const COLOR_BG := Color("070b12")
const COLOR_PANEL := Color("0d1420")
const COLOR_PANEL_ALT := Color("111a29")
const COLOR_BORDER := Color("24324a")
const COLOR_ACCENT := Color("73f1d1")
const COLOR_TEXT := Color("e9eef7")
const COLOR_MUTED := Color("8190aa")
const COLOR_SOFT := Color("b6c2d6")

const NAV_ITEMS := [
	["PRODUCT", "/"],
	["STUDIO", "/studio"],
	["ARCHITECTURE", "/architecture"],
	["PUBLICATION", "/publication"],
	["INSPECT", "/inspect"],
	["PLAYGROUND", "/playground"],
	["AGENTS", "/agents"],
]

const PAGE_DATA := {
	"/": {
		"eyebrow": "PRODUCT RUNTIME",
		"title": "NovelForge",
		"copy": "A spatial control room for agentic long-form fiction production. The product surface is now rendered as a native Godot Web application.",
		"metrics": ["RUNTIME  GODOT 4.7", "SURFACE  2D / 2.5D", "DOCS  ASTRO"],
	},
	"/start": {
		"eyebrow": "START HUB",
		"title": "Enter the production system",
		"copy": "Choose a product surface without leaving the shared runtime. Routes stay browser-addressable while the scene remains alive.",
		"metrics": ["ENTRY  ROUTED", "STATE  SHARED", "DOCS  EXTERNAL"],
	},
	"/product": {
		"eyebrow": "PRODUCT",
		"title": "One runtime, explicit boundaries",
		"copy": "NovelForge exposes production, inspection, publication, and agent surfaces as one coherent application rather than a stack of disconnected pages.",
		"metrics": ["SHELL  UNIFIED", "ROUTES  10", "CANVAS  LIVE"],
	},
	"/studio": {
		"eyebrow": "STUDIO",
		"title": "Production terminal",
		"copy": "Authoring work is represented as an explicit flow: context enters a worker, candidate output reaches a gate, and only approved state can settle.",
		"metrics": ["MODE  AUTHOR", "FLOW  EXPLICIT", "SETTLE  GUARDED"],
	},
	"/architecture": {
		"eyebrow": "ARCHITECTURE",
		"title": "Live system topology",
		"copy": "Read the framework spatially. Hover the graph to reveal depth, follow moving packets through boundaries, and select a subsystem to inspect its role.",
		"metrics": ["GRAPH  LIVE", "DEPTH  2.5D", "STATE  ROUTED"],
	},
	"/publication": {
		"eyebrow": "PUBLICATION",
		"title": "Derived output only",
		"copy": "Publication is downstream of accepted state. The product surface keeps that boundary visible instead of presenting export as an isolated formatter.",
		"metrics": ["SOURCE  ACCEPTED", "OUTPUT  DERIVED", "FORMATS  MULTI"],
	},
	"/inspect": {
		"eyebrow": "INSPECT",
		"title": "Exact projections",
		"copy": "Inspect runtime state, fingerprints, handoffs, and evidence without implying mutation authority. Selection in the map updates this observatory in place.",
		"metrics": ["MODE  READ ONLY", "EVIDENCE  BOUND", "AUTHORITY  FALSE"],
	},
	"/playground": {
		"eyebrow": "PLAYGROUND",
		"title": "Safe local experiments",
		"copy": "Exercise deterministic projections and preview flows against explicit inputs while keeping experiments outside accepted canon and settlement authority.",
		"metrics": ["SCOPE  LOCAL", "CANON  UNTOUCHED", "TRACE  VISIBLE"],
	},
	"/agents": {
		"eyebrow": "AGENTS",
		"title": "Observable execution",
		"copy": "Manager, worker, gate, and handoff relationships stay visible as a system. The UI emphasizes explicit state transitions over chat-shaped abstraction.",
		"metrics": ["RUN  EXPLICIT", "HANDOFF  VISIBLE", "RECEIPT  TRACEABLE"],
	},
	"/changelog": {
		"eyebrow": "CHANGELOG",
		"title": "Runtime evolution",
		"copy": "Product changes remain a first-class route inside the shared scene. Documentation continues to live in the semantic web where long-form reading belongs.",
		"metrics": ["VERSION  0.8.x", "UI  GODOT FIRST", "DOCS  STARLIGHT"],
	},
}

var _current_route := "/"
var _nav_buttons: Dictionary = {}
var _page_eyebrow: Label
var _page_title: Label
var _page_copy: Label
var _metric_labels: Array[Label] = []
var _route_label: Label
var _selection_label: Label
var _map
var _left_panel: Control
var _right_panel: Control

func _ready() -> void:
	_build_interface()
	_navigate(_browser_path(), false)
	_install_browser_history_guard()
	resized.connect(_apply_responsive_layout)
	call_deferred("_apply_responsive_layout")
	call_deferred("_signal_web_ready")

func _build_interface() -> void:
	var background := ColorRect.new()
	background.color = COLOR_BG
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)

	var shell := VBoxContainer.new()
	shell.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shell.add_theme_constant_override("separation", 0)
	add_child(shell)

	shell.add_child(_build_topbar())

	var body_margin := MarginContainer.new()
	body_margin.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body_margin.add_theme_constant_override("margin_left", 18)
	body_margin.add_theme_constant_override("margin_right", 18)
	body_margin.add_theme_constant_override("margin_top", 18)
	body_margin.add_theme_constant_override("margin_bottom", 18)
	shell.add_child(body_margin)

	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 14)
	body_margin.add_child(body)

	_left_panel = _build_page_panel()
	body.add_child(_left_panel)

	var map_panel := PanelContainer.new()
	map_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	map_panel.add_theme_stylebox_override("panel", _style(COLOR_PANEL, COLOR_BORDER, 18, 1))
	body.add_child(map_panel)

	var map_margin := MarginContainer.new()
	map_margin.add_theme_constant_override("margin_left", 1)
	map_margin.add_theme_constant_override("margin_right", 1)
	map_margin.add_theme_constant_override("margin_top", 1)
	map_margin.add_theme_constant_override("margin_bottom", 1)
	map_panel.add_child(map_margin)

	_map = SystemMap.new()
	_map.custom_minimum_size = Vector2(420, 520)
	_map.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_map.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_map.node_selected.connect(_on_map_node_selected)
	map_margin.add_child(_map)

	_right_panel = _build_runtime_panel()
	body.add_child(_right_panel)

	var footer := _build_footer()
	shell.add_child(footer)

func _build_topbar() -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.y = 68
	panel.add_theme_stylebox_override("panel", _style(Color("0a101a"), COLOR_BORDER, 0, 0, false, true))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 22)
	margin.add_theme_constant_override("margin_right", 22)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	margin.add_child(row)

	var brand := VBoxContainer.new()
	brand.custom_minimum_size.x = 180
	brand.add_theme_constant_override("separation", -2)
	row.add_child(brand)

	var brand_title := Label.new()
	brand_title.text = "NOVELFORGE"
	brand_title.add_theme_font_size_override("font_size", 18)
	brand_title.add_theme_color_override("font_color", COLOR_TEXT)
	brand.add_child(brand_title)

	var brand_meta := Label.new()
	brand_meta.text = "CONTROL ROOM  ·  0.8.x"
	brand_meta.add_theme_font_size_override("font_size", 9)
	brand_meta.add_theme_color_override("font_color", COLOR_MUTED)
	brand.add_child(brand_meta)

	var nav_scroll := ScrollContainer.new()
	nav_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	nav_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	row.add_child(nav_scroll)

	var nav := HBoxContainer.new()
	nav.add_theme_constant_override("separation", 4)
	nav_scroll.add_child(nav)

	for item in NAV_ITEMS:
		var label := str(item[0])
		var route := str(item[1])
		var button := Button.new()
		button.text = label
		button.flat = true
		button.custom_minimum_size = Vector2(92, 40)
		button.add_theme_font_size_override("font_size", 10)
		button.add_theme_color_override("font_color", COLOR_MUTED)
		button.add_theme_color_override("font_hover_color", COLOR_TEXT)
		button.pressed.connect(func(): _navigate(route, true))
		nav.add_child(button)
		_nav_buttons[route] = button

	var docs := Button.new()
	docs.text = "DOCS ↗"
	docs.custom_minimum_size = Vector2(86, 40)
	docs.add_theme_font_size_override("font_size", 10)
	docs.add_theme_color_override("font_color", Color("071016"))
	docs.add_theme_stylebox_override("normal", _style(COLOR_ACCENT, COLOR_ACCENT, 10, 0))
	docs.add_theme_stylebox_override("hover", _style(Color("9bffe8"), Color("9bffe8"), 10, 0))
	docs.pressed.connect(_open_docs)
	row.add_child(docs)

	return panel

func _build_page_panel() -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.x = 278
	panel.add_theme_stylebox_override("panel", _style(COLOR_PANEL, COLOR_BORDER, 18, 1))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 22)
	margin.add_theme_constant_override("margin_right", 22)
	margin.add_theme_constant_override("margin_top", 24)
	margin.add_theme_constant_override("margin_bottom", 22)
	panel.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	margin.add_child(column)

	_page_eyebrow = Label.new()
	_page_eyebrow.add_theme_font_size_override("font_size", 10)
	_page_eyebrow.add_theme_color_override("font_color", COLOR_ACCENT)
	column.add_child(_page_eyebrow)

	_page_title = Label.new()
	_page_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_page_title.add_theme_font_size_override("font_size", 30)
	_page_title.add_theme_color_override("font_color", COLOR_TEXT)
	column.add_child(_page_title)

	_page_copy = Label.new()
	_page_copy.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_page_copy.add_theme_font_size_override("font_size", 13)
	_page_copy.add_theme_color_override("font_color", COLOR_SOFT)
	_page_copy.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(_page_copy)

	var rule := HSeparator.new()
	rule.add_theme_color_override("separator", COLOR_BORDER)
	column.add_child(rule)

	var metrics_title := Label.new()
	metrics_title.text = "SURFACE CONTRACT"
	metrics_title.add_theme_font_size_override("font_size", 9)
	metrics_title.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(metrics_title)

	for _index in range(3):
		var metric := Label.new()
		metric.add_theme_font_size_override("font_size", 10)
		metric.add_theme_color_override("font_color", COLOR_TEXT)
		column.add_child(metric)
		_metric_labels.append(metric)

	var hint := Label.new()
	hint.text = "Hover the topology. Select a node to bind the runtime inspector."
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.add_theme_font_size_override("font_size", 10)
	hint.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(hint)

	return panel

func _build_runtime_panel() -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.x = 292
	panel.add_theme_stylebox_override("panel", _style(COLOR_PANEL, COLOR_BORDER, 18, 1))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_top", 22)
	margin.add_theme_constant_override("margin_bottom", 22)
	panel.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	margin.add_child(column)

	var title := Label.new()
	title.text = "RUNTIME"
	title.add_theme_font_size_override("font_size", 10)
	title.add_theme_color_override("font_color", COLOR_ACCENT)
	column.add_child(title)

	var ready := Label.new()
	ready.text = "●  READY"
	ready.add_theme_font_size_override("font_size", 18)
	ready.add_theme_color_override("font_color", COLOR_TEXT)
	column.add_child(ready)

	column.add_child(_status_row("ENGINE", "Godot Web"))
	column.add_child(_status_row("RENDERER", "Compatibility"))
	column.add_child(_status_row("DIMENSION", "2D + depth"))
	column.add_child(_status_row("DOCS", "Astro boundary"))

	var rule := HSeparator.new()
	rule.add_theme_color_override("separator", COLOR_BORDER)
	column.add_child(rule)

	var route_title := Label.new()
	route_title.text = "BROWSER ROUTE"
	route_title.add_theme_font_size_override("font_size", 9)
	route_title.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(route_title)

	_route_label = Label.new()
	_route_label.add_theme_font_size_override("font_size", 13)
	_route_label.add_theme_color_override("font_color", COLOR_TEXT)
	column.add_child(_route_label)

	var selection_title := Label.new()
	selection_title.text = "SELECTED OBJECT"
	selection_title.add_theme_font_size_override("font_size", 9)
	selection_title.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(selection_title)

	_selection_label = Label.new()
	_selection_label.text = "PROJECT"
	_selection_label.add_theme_font_size_override("font_size", 15)
	_selection_label.add_theme_color_override("font_color", COLOR_ACCENT)
	column.add_child(_selection_label)

	var note := Label.new()
	note.text = "Browser history is synchronized with scene navigation. Docs intentionally cross into a separate HTML application."
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.size_flags_vertical = Control.SIZE_EXPAND_FILL
	note.add_theme_font_size_override("font_size", 10)
	note.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(note)

	var changelog := Button.new()
	changelog.text = "CHANGELOG"
	changelog.flat = true
	changelog.add_theme_color_override("font_color", COLOR_SOFT)
	changelog.add_theme_color_override("font_hover_color", COLOR_TEXT)
	changelog.pressed.connect(func(): _navigate("/changelog", true))
	column.add_child(changelog)

	return panel

func _build_footer() -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.y = 38
	panel.add_theme_stylebox_override("panel", _style(Color("090e17"), COLOR_BORDER, 0, 0, true, false))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 22)
	margin.add_theme_constant_override("margin_right", 22)
	panel.add_child(margin)

	var row := HBoxContainer.new()
	margin.add_child(row)

	var left := Label.new()
	left.text = "NOVELFORGE PRODUCT RUNTIME"
	left.add_theme_font_size_override("font_size", 9)
	left.add_theme_color_override("font_color", COLOR_MUTED)
	row.add_child(left)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	var right := Label.new()
	right.text = "GODOT-FIRST  ·  SEMANTIC DOCS REMAIN WEB-NATIVE"
	right.add_theme_font_size_override("font_size", 9)
	right.add_theme_color_override("font_color", COLOR_MUTED)
	row.add_child(right)

	return panel

func _status_row(key: String, value: String) -> Control:
	var row := HBoxContainer.new()
	var key_label := Label.new()
	key_label.text = key
	key_label.custom_minimum_size.x = 88
	key_label.add_theme_font_size_override("font_size", 9)
	key_label.add_theme_color_override("font_color", COLOR_MUTED)
	row.add_child(key_label)
	var value_label := Label.new()
	value_label.text = value
	value_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	value_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	value_label.add_theme_font_size_override("font_size", 10)
	value_label.add_theme_color_override("font_color", COLOR_TEXT)
	row.add_child(value_label)
	return row

func _style(bg: Color, border: Color, radius: int, border_width: int, top_border: bool = true, bottom_border: bool = true) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.border_width_left = border_width
	style.border_width_right = border_width
	style.border_width_top = border_width if top_border else 0
	style.border_width_bottom = border_width if bottom_border else 0
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	return style

func _navigate(path: String, push_history: bool = true) -> void:
	var route := _normalize_route(path)
	if not PAGE_DATA.has(route):
		route = "/"
	_current_route = route
	_update_page()
	_map.set_focus(route)
	if push_history and OS.has_feature("web"):
		JavaScriptBridge.eval("window.history.pushState({}, '', '%s');" % route)

func _update_page() -> void:
	var data: Dictionary = PAGE_DATA[_current_route]
	_page_eyebrow.text = str(data["eyebrow"])
	_page_title.text = str(data["title"])
	_page_copy.text = str(data["copy"])
	var metrics: Array = data["metrics"]
	for index in range(_metric_labels.size()):
		_metric_labels[index].text = str(metrics[index])
	_route_label.text = _current_route

	for route in _nav_buttons:
		var button: Button = _nav_buttons[route]
		var active := str(route) == _current_route or (_current_route == "/product" and str(route) == "/")
		button.add_theme_color_override("font_color", COLOR_ACCENT if active else COLOR_MUTED)

func _on_map_node_selected(node_id: String) -> void:
	_selection_label.text = node_id.to_upper()
	match node_id:
		"project":
			_navigate("/", true)
		"publication":
			_navigate("/publication", true)
		"inspector":
			_navigate("/inspect", true)
		"agents":
			_navigate("/agents", true)
		_:
			pass

func _apply_responsive_layout() -> void:
	var compact := size.x < 1080.0
	var phone := size.x < 720.0
	_left_panel.visible = not compact
	_right_panel.visible = not compact
	if phone:
		_map.custom_minimum_size = Vector2(300, 520)
	else:
		_map.custom_minimum_size = Vector2(420, 520)

func _install_browser_history_guard() -> void:
	if not OS.has_feature("web"):
		return
	# Keep browser history authoritative without holding a JavaScript callback
	# object inside the scene. A popstate performs a cheap hard reload of the
	# current product path; the new scene restores route focus from pathname.
	JavaScriptBridge.eval("if(!window.__novelforgePopstateReloadInstalled){window.__novelforgePopstateReloadInstalled=true;window.addEventListener('popstate',()=>window.location.reload());}")

func _browser_path() -> String:
	if not OS.has_feature("web"):
		return "/"
	return str(JavaScriptBridge.eval("window.location.pathname"))

func _signal_web_ready() -> void:
	if not OS.has_feature("web"):
		return
	JavaScriptBridge.eval("document.documentElement.dataset.novelforgeRuntime='ready';const loader=document.getElementById('nf-loader');if(loader){loader.classList.add('is-ready');}window.dispatchEvent(new CustomEvent('novelforge:ready')); ")

func _open_docs() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.location.assign('/docs');")
	else:
		print("Docs: /docs")

func _normalize_route(path: String) -> String:
	var clean := path.split("?", false, 1)[0]
	if clean.length() > 1:
		clean = clean.trim_suffix("/")
	return clean if not clean.is_empty() else "/"
