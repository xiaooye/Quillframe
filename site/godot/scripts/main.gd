extends Control

const SystemMap = preload("res://scripts/system_map.gd")
const AmbientBackdrop = preload("res://scripts/ambient_backdrop.gd")

const COLOR_BG := Color("060911")
const COLOR_PANEL := Color(0.045, 0.064, 0.098, 0.94)
const COLOR_PANEL_SOFT := Color(0.058, 0.082, 0.125, 0.82)
const COLOR_BORDER := Color("233149")
const COLOR_BORDER_SOFT := Color(0.22, 0.31, 0.45, 0.46)
const COLOR_TEXT := Color("eef4fb")
const COLOR_MUTED := Color("73839d")
const COLOR_SOFT := Color("b8c5d8")

const NAV_ITEMS := [
	["PRODUCT", "/"],
	["STUDIO", "/studio"],
	["ARCHITECTURE", "/architecture"],
	["PUBLICATION", "/publication"],
	["INSPECT", "/inspect"],
	["PLAYGROUND", "/playground"],
	["AGENTS", "/agents"],
]

const ROUTE_ACCENTS := {
	"/": Color("73f1d1"),
	"/start": Color("73f1d1"),
	"/product": Color("73f1d1"),
	"/studio": Color("7bc8ff"),
	"/architecture": Color("b39cff"),
	"/publication": Color("ffc66e"),
	"/inspect": Color("80d4ff"),
	"/playground": Color("f39ac7"),
	"/agents": Color("a4e67d"),
	"/changelog": Color("a8b5c9"),
}

const ROUTE_SELECTION := {
	"/": "project",
	"/start": "project",
	"/product": "project",
	"/studio": "worker",
	"/architecture": "manager",
	"/publication": "publication",
	"/inspect": "inspector",
	"/playground": "context",
	"/agents": "agents",
	"/changelog": "project",
}

const PAGE_DATA := {
	"/": {
		"eyebrow": "PRODUCT / CONTROL SURFACE",
		"title": "NovelForge",
		"copy": "A spatial production environment for agentic long-form fiction. Move through the system as one live workspace instead of a pile of disconnected tools.",
		"metrics": ["RUNTIME  GODOT 4.7", "SURFACE  2D / 2.5D", "DOCS  WEB-NATIVE"],
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["EXPLORE SYSTEM", "/architecture"],
	},
	"/start": {
		"eyebrow": "START / ROUTED ENTRY",
		"title": "Enter the production system",
		"copy": "Choose a working surface without tearing down the shared runtime. Browser-addressable routes stay synchronized with the live scene.",
		"metrics": ["ENTRY  ROUTED", "STATE  SHARED", "DOCS  EXTERNAL"],
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["VIEW ARCHITECTURE", "/architecture"],
	},
	"/product": {
		"eyebrow": "PRODUCT / UNIFIED SHELL",
		"title": "One runtime, explicit boundaries",
		"copy": "Production, inspection, publication, and agent surfaces share one visual language while the documentation app remains intentionally separate.",
		"metrics": ["SHELL  UNIFIED", "ROUTES  LIVE", "CANVAS  PERSISTENT"],
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["VIEW ARCHITECTURE", "/architecture"],
	},
	"/studio": {
		"eyebrow": "STUDIO / PRODUCTION",
		"title": "Production terminal",
		"copy": "Context enters a worker, candidate output reaches a gate, and approved state can move toward settlement. The workflow remains spatially legible while you work.",
		"metrics": ["MODE  AUTHOR", "FLOW  EXPLICIT", "SETTLE  GUARDED"],
		"primary": ["INSPECT RUNTIME", "/inspect"],
		"secondary": ["VIEW AGENTS", "/agents"],
	},
	"/architecture": {
		"eyebrow": "ARCHITECTURE / TOPOLOGY",
		"title": "Live system topology",
		"copy": "Read NovelForge as a moving system. Follow routed packets across orchestration, execution, verification, settlement, and publication boundaries.",
		"metrics": ["GRAPH  INTERACTIVE", "DEPTH  2.5D", "STATE  ROUTED"],
		"primary": ["OPEN PLAYGROUND", "/playground"],
		"secondary": ["INSPECT STATE", "/inspect"],
	},
	"/publication": {
		"eyebrow": "PUBLICATION / DERIVED OUTPUT",
		"title": "Accepted state, rendered outward",
		"copy": "Publication stays visually downstream of accepted state. Export is presented as a derived surface, never as a parallel source of truth.",
		"metrics": ["SOURCE  ACCEPTED", "OUTPUT  DERIVED", "FORMATS  MULTI"],
		"primary": ["INSPECT SOURCE", "/inspect"],
		"secondary": ["VIEW SYSTEM", "/architecture"],
	},
	"/inspect": {
		"eyebrow": "INSPECT / OBSERVABILITY",
		"title": "Exact projections",
		"copy": "Inspect runtime state, fingerprints, handoffs, and evidence without presenting an observation surface as mutation authority.",
		"metrics": ["MODE  OBSERVE", "EVIDENCE  BOUND", "STATE  TRACEABLE"],
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["VIEW AGENTS", "/agents"],
	},
	"/playground": {
		"eyebrow": "PLAYGROUND / LOCAL EXPERIMENT",
		"title": "Safe local experiments",
		"copy": "Exercise deterministic projections and preview flows against explicit inputs while keeping experiments visually distinct from accepted production state.",
		"metrics": ["SCOPE  LOCAL", "CANON  UNTOUCHED", "TRACE  VISIBLE"],
		"primary": ["VIEW ARCHITECTURE", "/architecture"],
		"secondary": ["OPEN STUDIO", "/studio"],
	},
	"/agents": {
		"eyebrow": "AGENTS / EXECUTION",
		"title": "Observable execution",
		"copy": "Manager, worker, gate, and handoff relationships appear as a coordinated system. The UI emphasizes explicit state transitions over chat-shaped abstraction.",
		"metrics": ["RUN  EXPLICIT", "HANDOFF  VISIBLE", "RECEIPT  TRACEABLE"],
		"primary": ["OPEN STUDIO", "/studio"],
		"secondary": ["INSPECT STATE", "/inspect"],
	},
	"/changelog": {
		"eyebrow": "CHANGELOG / PRODUCT EVOLUTION",
		"title": "Runtime evolution",
		"copy": "Product changes remain visible inside the shared scene while long-form reference material stays in the semantic documentation application.",
		"metrics": ["VERSION  0.8.x", "UI  GODOT-FIRST", "DOCS  STARLIGHT"],
		"primary": ["BACK TO PRODUCT", "/"],
		"secondary": ["VIEW ARCHITECTURE", "/architecture"],
	},
}

const NODE_DATA := {
	"project": ["PROJECT ROOT", "Pinned project state and product entry boundary.", "ROOT / AUTHORITY"],
	"manager": ["MANAGER", "Orchestration surface coordinating context, workers, gates, and handoffs.", "CONTROL / ROUTING"],
	"context": ["CONTEXT", "Sparse working context assembled for the current execution surface.", "INPUT / BOUNDED"],
	"worker": ["WORKER", "Execution surface producing a candidate from explicit inputs and mode constraints.", "EXECUTION / CANDIDATE"],
	"agents": ["AGENT POOL", "Specialized execution roles exposed as observable participants in the run.", "POOL / SPECIALIZED"],
	"gate": ["GATE", "Verification boundary evaluating a candidate before downstream acceptance.", "VERIFY / EVIDENCE"],
	"inspector": ["INSPECTOR", "Read-only projection surface for state, receipts, and runtime evidence.", "OBSERVE / READ-ONLY"],
	"settlement": ["SETTLEMENT", "Controlled boundary that separates accepted state from transient candidates.", "COMMIT / GUARDED"],
	"publication": ["PUBLICATION", "Derived output surface rendered from accepted upstream state.", "DERIVE / OUTPUT"],
}

var _current_route := "/"
var _accent := Color("73f1d1")
var _nav_buttons: Dictionary = {}
var _metric_labels: Array[Label] = []
var _map
var _backdrop
var _left_panel: Control
var _right_panel: Control
var _body_margin: MarginContainer
var _topbar: PanelContainer
var _brand: HBoxContainer
var _brand_wordmark: VBoxContainer
var _brand_title: Label
var _brand_meta: Label
var _docs_button: Button
var _live_label: Label
var _footer: PanelContainer
var _footer_left: Label
var _footer_right: Label
var _page_eyebrow: Label
var _page_title: Label
var _page_copy: Label
var _route_label: Label
var _selection_label: Label
var _selection_meta: Label
var _selection_copy: Label
var _primary_button: Button
var _secondary_button: Button
var _primary_target := "/studio"
var _secondary_target := "/architecture"
var _layout_mode := "desktop"

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

	_body_margin = MarginContainer.new()
	_body_margin.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_set_body_margins(16)
	shell.add_child(_body_margin)

	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 12)
	_body_margin.add_child(body)

	_left_panel = _build_page_panel()
	body.add_child(_left_panel)

	body.add_child(_build_map_panel())

	_right_panel = _build_runtime_panel()
	body.add_child(_right_panel)

	_footer = _build_footer()
	shell.add_child(_footer)

func _build_topbar() -> PanelContainer:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.y = 72
	panel.add_theme_stylebox_override("panel", _style(Color(0.032, 0.047, 0.073, 0.965), COLOR_BORDER_SOFT, 0, 1, false, true))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	margin.add_child(row)

	_brand = HBoxContainer.new()
	_brand.custom_minimum_size.x = 206
	_brand.add_theme_constant_override("separation", 10)
	row.add_child(_brand)

	var mark := PanelContainer.new()
	mark.custom_minimum_size = Vector2(36, 36)
	mark.add_theme_stylebox_override("panel", _style(Color(0.10, 0.18, 0.24, 0.90), Color(0.28, 0.55, 0.62, 0.70), 10, 1))
	_brand.add_child(mark)
	var mark_label := Label.new()
	mark_label.text = "N"
	mark_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mark_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	mark_label.add_theme_font_size_override("font_size", 14)
	mark_label.add_theme_color_override("font_color", COLOR_TEXT)
	mark.add_child(mark_label)

	_brand_wordmark = VBoxContainer.new()
	_brand_wordmark.add_theme_constant_override("separation", -2)
	_brand.add_child(_brand_wordmark)

	_brand_title = Label.new()
	_brand_title.text = "NOVELFORGE"
	_brand_title.add_theme_font_size_override("font_size", 17)
	_brand_title.add_theme_color_override("font_color", COLOR_TEXT)
	_brand_wordmark.add_child(_brand_title)

	_brand_meta = Label.new()
	_brand_meta.text = "SPATIAL PRODUCTION SYSTEM"
	_brand_meta.add_theme_font_size_override("font_size", 8)
	_brand_meta.add_theme_color_override("font_color", COLOR_MUTED)
	_brand_wordmark.add_child(_brand_meta)

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
		button.flat = false
		button.custom_minimum_size = Vector2(94, 38)
		button.add_theme_font_size_override("font_size", 9)
		button.add_theme_color_override("font_color", COLOR_MUTED)
		button.add_theme_color_override("font_hover_color", COLOR_TEXT)
		button.add_theme_stylebox_override("normal", _style(Color(0, 0, 0, 0), Color(0, 0, 0, 0), 9, 1))
		button.add_theme_stylebox_override("hover", _style(Color(0.08, 0.11, 0.17, 0.88), COLOR_BORDER_SOFT, 9, 1))
		button.add_theme_stylebox_override("pressed", _style(Color(0.10, 0.14, 0.20, 0.96), COLOR_BORDER_SOFT, 9, 1))
		button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
		button.pressed.connect(func(): _navigate(route, true))
		nav.add_child(button)
		_nav_buttons[route] = button

	var live_panel := PanelContainer.new()
	live_panel.custom_minimum_size = Vector2(74, 34)
	live_panel.add_theme_stylebox_override("panel", _style(Color(0.05, 0.08, 0.12, 0.88), COLOR_BORDER_SOFT, 9, 1))
	row.add_child(live_panel)
	_live_label = Label.new()
	_live_label.text = "●  LIVE"
	_live_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_live_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_live_label.add_theme_font_size_override("font_size", 9)
	live_panel.add_child(_live_label)

	_docs_button = Button.new()
	_docs_button.text = "DOCS  ↗"
	_docs_button.custom_minimum_size = Vector2(86, 38)
	_docs_button.add_theme_font_size_override("font_size", 9)
	_docs_button.add_theme_color_override("font_color", Color("061018"))
	_docs_button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_docs_button.pressed.connect(_open_docs)
	row.add_child(_docs_button)

	return panel

func _build_page_panel() -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.x = 306
	panel.add_theme_stylebox_override("panel", _style(COLOR_PANEL, COLOR_BORDER_SOFT, 18, 1))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 24)
	margin.add_theme_constant_override("margin_right", 24)
	margin.add_theme_constant_override("margin_top", 24)
	margin.add_theme_constant_override("margin_bottom", 22)
	panel.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 14)
	margin.add_child(column)

	_page_eyebrow = Label.new()
	_page_eyebrow.add_theme_font_size_override("font_size", 9)
	column.add_child(_page_eyebrow)

	_page_title = Label.new()
	_page_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_page_title.add_theme_font_size_override("font_size", 32)
	_page_title.add_theme_color_override("font_color", COLOR_TEXT)
	column.add_child(_page_title)

	_page_copy = Label.new()
	_page_copy.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_page_copy.add_theme_font_size_override("font_size", 12)
	_page_copy.add_theme_color_override("font_color", COLOR_SOFT)
	_page_copy.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(_page_copy)

	column.add_child(_rule())

	var metrics_title := Label.new()
	metrics_title.text = "SURFACE CONTRACT"
	metrics_title.add_theme_font_size_override("font_size", 8)
	metrics_title.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(metrics_title)

	for _index in range(3):
		var metric_panel := PanelContainer.new()
		metric_panel.custom_minimum_size.y = 31
		metric_panel.add_theme_stylebox_override("panel", _style(Color(0.06, 0.085, 0.13, 0.72), Color(0.20, 0.29, 0.42, 0.40), 8, 1))
		column.add_child(metric_panel)
		var metric_margin := MarginContainer.new()
		metric_margin.add_theme_constant_override("margin_left", 10)
		metric_margin.add_theme_constant_override("margin_right", 10)
		metric_panel.add_child(metric_margin)
		var metric := Label.new()
		metric.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		metric.add_theme_font_size_override("font_size", 9)
		metric.add_theme_color_override("font_color", COLOR_TEXT)
		metric_margin.add_child(metric)
		_metric_labels.append(metric)

	var actions := VBoxContainer.new()
	actions.add_theme_constant_override("separation", 8)
	column.add_child(actions)

	_primary_button = Button.new()
	_primary_button.custom_minimum_size.y = 42
	_primary_button.add_theme_font_size_override("font_size", 10)
	_primary_button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_primary_button.pressed.connect(func(): _navigate(_primary_target, true))
	actions.add_child(_primary_button)

	_secondary_button = Button.new()
	_secondary_button.custom_minimum_size.y = 38
	_secondary_button.add_theme_font_size_override("font_size", 9)
	_secondary_button.add_theme_color_override("font_color", COLOR_SOFT)
	_secondary_button.add_theme_stylebox_override("normal", _style(Color(0.035, 0.05, 0.08, 0.72), COLOR_BORDER_SOFT, 9, 1))
	_secondary_button.add_theme_stylebox_override("hover", _style(Color(0.07, 0.10, 0.15, 0.90), Color(0.32, 0.42, 0.58, 0.65), 9, 1))
	_secondary_button.add_theme_stylebox_override("pressed", _style(Color(0.08, 0.12, 0.18, 0.96), COLOR_BORDER_SOFT, 9, 1))
	_secondary_button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_secondary_button.pressed.connect(func(): _navigate(_secondary_target, true))
	actions.add_child(_secondary_button)

	var hint := Label.new()
	hint.text = "Select topology nodes to move between live product surfaces."
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.add_theme_font_size_override("font_size", 9)
	hint.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(hint)

	return panel

func _build_map_panel() -> Control:
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_theme_stylebox_override("panel", _style(Color(0.035, 0.050, 0.078, 0.94), COLOR_BORDER_SOFT, 18, 1))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 1)
	margin.add_theme_constant_override("margin_right", 1)
	margin.add_theme_constant_override("margin_top", 1)
	margin.add_theme_constant_override("margin_bottom", 1)
	panel.add_child(margin)

	_map = SystemMap.new()
	_map.custom_minimum_size = Vector2(440, 520)
	_map.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_map.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_map.node_selected.connect(_on_map_node_selected)
	margin.add_child(_map)
	return panel

func _build_runtime_panel() -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.x = 306
	panel.add_theme_stylebox_override("panel", _style(COLOR_PANEL, COLOR_BORDER_SOFT, 18, 1))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 22)
	margin.add_theme_constant_override("margin_right", 22)
	margin.add_theme_constant_override("margin_top", 22)
	margin.add_theme_constant_override("margin_bottom", 22)
	panel.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 11)
	margin.add_child(column)

	var title := Label.new()
	title.text = "SYSTEM STATUS"
	title.add_theme_font_size_override("font_size", 8)
	title.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(title)

	var ready := HBoxContainer.new()
	ready.add_theme_constant_override("separation", 8)
	column.add_child(ready)
	var ready_dot := Label.new()
	ready_dot.text = "●"
	ready_dot.add_theme_font_size_override("font_size", 13)
	ready.add_child(ready_dot)
	var ready_text := Label.new()
	ready_text.text = "Runtime ready"
	ready_text.add_theme_font_size_override("font_size", 17)
	ready_text.add_theme_color_override("font_color", COLOR_TEXT)
	ready.add_child(ready_text)

	column.add_child(_status_row("ENGINE", "Godot Web"))
	column.add_child(_status_row("RENDERER", "Compatibility"))
	column.add_child(_status_row("SURFACE", "2D + spatial depth"))
	column.add_child(_status_row("DOCS", "Astro boundary"))

	column.add_child(_rule())

	var route_title := Label.new()
	route_title.text = "BROWSER ROUTE"
	route_title.add_theme_font_size_override("font_size", 8)
	route_title.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(route_title)

	_route_label = Label.new()
	_route_label.add_theme_font_size_override("font_size", 12)
	_route_label.add_theme_color_override("font_color", COLOR_TEXT)
	column.add_child(_route_label)

	var selection_title := Label.new()
	selection_title.text = "BOUND OBJECT"
	selection_title.add_theme_font_size_override("font_size", 8)
	selection_title.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(selection_title)

	var selection_card := PanelContainer.new()
	selection_card.add_theme_stylebox_override("panel", _style(COLOR_PANEL_SOFT, COLOR_BORDER_SOFT, 12, 1))
	selection_card.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(selection_card)
	var selection_margin := MarginContainer.new()
	selection_margin.add_theme_constant_override("margin_left", 14)
	selection_margin.add_theme_constant_override("margin_right", 14)
	selection_margin.add_theme_constant_override("margin_top", 14)
	selection_margin.add_theme_constant_override("margin_bottom", 14)
	selection_card.add_child(selection_margin)
	var selection_column := VBoxContainer.new()
	selection_column.add_theme_constant_override("separation", 8)
	selection_margin.add_child(selection_column)

	_selection_label = Label.new()
	_selection_label.add_theme_font_size_override("font_size", 16)
	selection_column.add_child(_selection_label)

	_selection_meta = Label.new()
	_selection_meta.add_theme_font_size_override("font_size", 8)
	selection_column.add_child(_selection_meta)

	_selection_copy = Label.new()
	_selection_copy.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_selection_copy.add_theme_font_size_override("font_size", 10)
	_selection_copy.add_theme_color_override("font_color", COLOR_SOFT)
	selection_column.add_child(_selection_copy)

	var note := Label.new()
	note.text = "Browser history remains synchronized with the live scene. Documentation intentionally hard-navigates into a separate semantic HTML application."
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.add_theme_font_size_override("font_size", 9)
	note.add_theme_color_override("font_color", COLOR_MUTED)
	column.add_child(note)

	var changelog := Button.new()
	changelog.text = "PRODUCT CHANGELOG  →"
	changelog.flat = true
	changelog.alignment = HORIZONTAL_ALIGNMENT_LEFT
	changelog.add_theme_font_size_override("font_size", 9)
	changelog.add_theme_color_override("font_color", COLOR_SOFT)
	changelog.add_theme_color_override("font_hover_color", COLOR_TEXT)
	changelog.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	changelog.pressed.connect(func(): _navigate("/changelog", true))
	column.add_child(changelog)

	return panel

func _build_footer() -> PanelContainer:
	var panel := PanelContainer.new()
	panel.custom_minimum_size.y = 34
	panel.add_theme_stylebox_override("panel", _style(Color(0.028, 0.041, 0.065, 0.965), COLOR_BORDER_SOFT, 0, 1, true, false))

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	panel.add_child(margin)

	var row := HBoxContainer.new()
	margin.add_child(row)

	_footer_left = Label.new()
	_footer_left.text = "NOVELFORGE  /  PRODUCT RUNTIME"
	_footer_left.add_theme_font_size_override("font_size", 8)
	_footer_left.add_theme_color_override("font_color", COLOR_MUTED)
	row.add_child(_footer_left)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	_footer_right = Label.new()
	_footer_right.text = "GODOT WEB  ·  ROUTED CANVAS  ·  ASTRO DOCS"
	_footer_right.add_theme_font_size_override("font_size", 8)
	_footer_right.add_theme_color_override("font_color", COLOR_MUTED)
	row.add_child(_footer_right)

	return panel

func _status_row(key: String, value: String) -> Control:
	var row := HBoxContainer.new()
	var key_label := Label.new()
	key_label.text = key
	key_label.custom_minimum_size.x = 82
	key_label.add_theme_font_size_override("font_size", 8)
	key_label.add_theme_color_override("font_color", COLOR_MUTED)
	row.add_child(key_label)
	var value_label := Label.new()
	value_label.text = value
	value_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	value_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	value_label.add_theme_font_size_override("font_size", 9)
	value_label.add_theme_color_override("font_color", COLOR_TEXT)
	row.add_child(value_label)
	return row

func _rule() -> HSeparator:
	var rule := HSeparator.new()
	rule.add_theme_color_override("separator", Color(0.20, 0.29, 0.43, 0.46))
	return rule

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
	_accent = ROUTE_ACCENTS.get(route, Color("73f1d1"))
	_update_page()
	_map.set_focus(route)
	var selected := str(ROUTE_SELECTION.get(route, "project"))
	if _map.has_method("select_node"):
		_map.select_node(selected)
	_set_selection(selected)
	_backdrop.set_accent(_accent)
	if push_history and OS.has_feature("web"):
		JavaScriptBridge.eval("window.history.pushState({}, '', '%s');" % route)

func _update_page() -> void:
	var data: Dictionary = PAGE_DATA[_current_route]
	_page_eyebrow.text = str(data["eyebrow"])
	_page_eyebrow.add_theme_color_override("font_color", _accent)
	_page_title.text = str(data["title"])
	_page_copy.text = str(data["copy"])

	var metrics: Array = data["metrics"]
	for index in range(_metric_labels.size()):
		_metric_labels[index].text = str(metrics[index])

	var primary: Array = data["primary"]
	var secondary: Array = data["secondary"]
	_primary_button.text = str(primary[0]) + "  →"
	_primary_target = str(primary[1])
	_secondary_button.text = str(secondary[0])
	_secondary_target = str(secondary[1])
	_primary_button.add_theme_color_override("font_color", Color("061018"))
	_primary_button.add_theme_stylebox_override("normal", _style(_accent, _accent, 10, 1))
	_primary_button.add_theme_stylebox_override("hover", _style(_accent.lightened(0.10), _accent.lightened(0.10), 10, 1))
	_primary_button.add_theme_stylebox_override("pressed", _style(_accent.darkened(0.08), _accent.darkened(0.08), 10, 1))

	_route_label.text = _current_route
	_live_label.add_theme_color_override("font_color", _accent)
	_docs_button.add_theme_stylebox_override("normal", _style(_accent, _accent, 9, 0))
	_docs_button.add_theme_stylebox_override("hover", _style(_accent.lightened(0.10), _accent.lightened(0.10), 9, 0))
	_docs_button.add_theme_stylebox_override("pressed", _style(_accent.darkened(0.08), _accent.darkened(0.08), 9, 0))

	for route in _nav_buttons:
		var button: Button = _nav_buttons[route]
		var active := str(route) == _current_route or (_current_route == "/product" and str(route) == "/")
		button.add_theme_color_override("font_color", _accent if active else COLOR_MUTED)
		if active:
			button.add_theme_stylebox_override("normal", _style(Color(_accent.r, _accent.g, _accent.b, 0.10), Color(_accent.r, _accent.g, _accent.b, 0.34), 9, 1))
		else:
			button.add_theme_stylebox_override("normal", _style(Color(0, 0, 0, 0), Color(0, 0, 0, 0), 9, 1))

func _set_selection(node_id: String) -> void:
	var data: Array = NODE_DATA.get(node_id, NODE_DATA["project"])
	_selection_label.text = str(data[0])
	_selection_label.add_theme_color_override("font_color", _accent)
	_selection_meta.text = str(data[2])
	_selection_meta.add_theme_color_override("font_color", _accent)
	_selection_copy.text = str(data[1])

func _on_map_node_selected(node_id: String) -> void:
	_set_selection(node_id)
	match node_id:
		"project":
			_navigate("/", true)
		"manager":
			_navigate("/architecture", true)
		"worker":
			_navigate("/studio", true)
		"context":
			_navigate("/playground", true)
		"publication":
			_navigate("/publication", true)
		"inspector":
			_navigate("/inspect", true)
		"agents":
			_navigate("/agents", true)
		"gate", "settlement":
			_set_selection(node_id)
		_:
			pass

func _set_body_margins(value: int) -> void:
	_body_margin.add_theme_constant_override("margin_left", value)
	_body_margin.add_theme_constant_override("margin_right", value)
	_body_margin.add_theme_constant_override("margin_top", value)
	_body_margin.add_theme_constant_override("margin_bottom", value)

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

	_left_panel.visible = not compact
	_right_panel.visible = not compact
	_footer_right.visible = not compact
	_brand_meta.visible = not phone
	_live_label.get_parent().visible = not compact

	if phone:
		_topbar.custom_minimum_size.y = 60
		_brand.custom_minimum_size.x = 96
		_brand_wordmark.visible = false
		_docs_button.custom_minimum_size = Vector2(62, 34)
		_docs_button.text = "DOCS"
		_footer.custom_minimum_size.y = 28
		_footer_left.text = "NOVELFORGE  /  LIVE"
		_map.custom_minimum_size = Vector2(280, maxf(340.0, viewport_height - 104.0))
		_set_body_margins(7)
		for route in _nav_buttons:
			var phone_button: Button = _nav_buttons[route]
			phone_button.custom_minimum_size = Vector2(78, 34)
			phone_button.add_theme_font_size_override("font_size", 8)
	elif compact:
		_topbar.custom_minimum_size.y = 66
		_brand.custom_minimum_size.x = 178
		_brand_wordmark.visible = true
		_brand_title.add_theme_font_size_override("font_size", 16)
		_docs_button.custom_minimum_size = Vector2(78, 36)
		_docs_button.text = "DOCS  ↗"
		_footer.custom_minimum_size.y = 32
		_footer_left.text = "NOVELFORGE  /  PRODUCT RUNTIME"
		_map.custom_minimum_size = Vector2(400, 470)
		_set_body_margins(11)
		for route in _nav_buttons:
			var compact_button: Button = _nav_buttons[route]
			compact_button.custom_minimum_size = Vector2(84, 36)
			compact_button.add_theme_font_size_override("font_size", 8)
	else:
		_topbar.custom_minimum_size.y = 72
		_brand.custom_minimum_size.x = 206
		_brand_wordmark.visible = true
		_brand_title.add_theme_font_size_override("font_size", 17)
		_docs_button.custom_minimum_size = Vector2(86, 38)
		_docs_button.text = "DOCS  ↗"
		_footer.custom_minimum_size.y = 34
		_footer_left.text = "NOVELFORGE  /  PRODUCT RUNTIME"
		_map.custom_minimum_size = Vector2(440, 520)
		_set_body_margins(16)
		for route in _nav_buttons:
			var desktop_button: Button = _nav_buttons[route]
			desktop_button.custom_minimum_size = Vector2(94, 38)
			desktop_button.add_theme_font_size_override("font_size", 9)

	_map.set_layout_mode(_layout_mode)
	_publish_layout_state()

func _publish_layout_state() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("document.documentElement.dataset.novelforgeLayout='%s';" % _layout_mode)

func _install_browser_history_guard() -> void:
	if not OS.has_feature("web"):
		return
	JavaScriptBridge.eval("if(!window.__novelforgePopstateReloadInstalled){window.__novelforgePopstateReloadInstalled=true;window.addEventListener('popstate',()=>window.location.reload());}")

func _browser_path() -> String:
	if not OS.has_feature("web"):
		return "/"
	return str(JavaScriptBridge.eval("window.location.pathname"))

func _signal_web_ready() -> void:
	_apply_responsive_layout()
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
