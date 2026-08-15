extends Node

const LOCALE_EN := "en-US"
const LOCALE_ZH := "zh-CN"
const STORAGE_KEY := "novelforge.locale"

const ZH := {
	"PRODUCT": "产品",
	"ARCHITECTURE": "架构",
	"PUBLICATION": "出版",
	"INSPECT": "检查",
	"PLAYGROUND": "实验",
	"AGENTS": "智能体",
	"DOCS": "文档",
	"DOCS  ↗": "文档  ↗",
	"●  LIVE": "●  运行中",
	"SPATIAL PRODUCTION SYSTEM": "空间化长篇生产系统",
	"SURFACE CONTRACT": "界面契约",
	"SYSTEM STATUS": "系统状态",
	"Runtime ready": "运行时就绪",
	"ENGINE": "引擎",
	"RENDERER": "渲染器",
	"SURFACE": "界面",
	"2D + spatial depth": "2D + 空间景深",
	"Astro boundary": "Astro 边界",
	"BROWSER ROUTE": "浏览器路由",
	"BOUND OBJECT": "绑定对象",
	"PRODUCT CHANGELOG  →": "产品更新  →",
	"NOVELFORGE  /  PRODUCT RUNTIME": "NOVELFORGE  /  产品运行时",
	"NOVELFORGE  /  LIVE": "NOVELFORGE  /  运行中",
	"GODOT WEB  ·  ROUTED CANVAS  ·  ASTRO DOCS": "GODOT WEB  ·  路由画布  ·  ASTRO 文档",
	"Select topology nodes to move between live product surfaces.": "选择拓扑节点，在当前运行时中切换产品界面。",
	"Browser history remains synchronized with the live scene. Documentation intentionally hard-navigates into a separate semantic HTML application.": "浏览器历史会与当前场景保持同步；文档则有意跳转到独立的语义化 HTML 应用。",
	"PRODUCT / CONTROL SURFACE": "产品 / 控制界面",
	"A spatial production environment for agentic long-form fiction. Move through the system as one live workspace instead of a pile of disconnected tools.": "面向智能体长篇小说生产的空间化环境。把整套系统当作一个持续运行的工作空间，而不是一堆彼此割裂的工具。",
	"START / ROUTED ENTRY": "开始 / 路由入口",
	"Enter the production system": "进入长篇生产系统",
	"Choose a working surface without tearing down the shared runtime. Browser-addressable routes stay synchronized with the live scene.": "在不重启共享运行时的前提下选择工作界面；可直接访问的浏览器路由会始终与当前场景同步。",
	"PRODUCT / UNIFIED SHELL": "产品 / 统一外壳",
	"One runtime, explicit boundaries": "一个运行时，边界明确",
	"Production, inspection, publication, and agent surfaces share one visual language while the documentation app remains intentionally separate.": "生产、检查、出版与智能体界面共享同一套视觉语言，而文档应用保持有意分离。",
	"STUDIO / PRODUCTION": "STUDIO / 生产",
	"Production terminal": "生产终端",
	"Context enters a worker, candidate output reaches a gate, and approved state can move toward settlement. The workflow remains spatially legible while you work.": "上下文进入 worker，候选输出抵达 gate，通过后再走向 settlement。整个工作流在操作过程中始终保持空间上的可读性。",
	"ARCHITECTURE / TOPOLOGY": "架构 / 拓扑",
	"Live system topology": "实时系统拓扑",
	"Read NovelForge as a moving system. Follow routed packets across orchestration, execution, verification, settlement, and publication boundaries.": "把 NovelForge 当作一个持续运动的系统来阅读：沿着路由数据包跨越编排、执行、验证、settlement 与出版边界。",
	"PUBLICATION / DERIVED OUTPUT": "出版 / 派生输出",
	"Accepted state, rendered outward": "从已接受状态向外渲染",
	"Publication stays visually downstream of accepted state. Export is presented as a derived surface, never as a parallel source of truth.": "Publication 在视觉上始终位于 accepted state 下游；导出只是派生界面，从不成为平行的 source of truth。",
	"INSPECT / OBSERVABILITY": "检查 / 可观测性",
	"Exact projections": "精确投影",
	"Inspect runtime state, fingerprints, handoffs, and evidence without presenting an observation surface as mutation authority.": "检查运行时状态、fingerprint、handoff 与 evidence，同时明确观察界面本身不拥有修改 authority。",
	"PLAYGROUND / LOCAL EXPERIMENT": "实验 / 本地推演",
	"Safe local experiments": "安全的本地实验",
	"Exercise deterministic projections and preview flows against explicit inputs while keeping experiments visually distinct from accepted production state.": "针对明确输入运行确定性 projection 与 preview flow，并在视觉上让实验状态与已接受的生产状态保持清楚区别。",
	"AGENTS / EXECUTION": "智能体 / 执行",
	"Observable execution": "可观测执行",
	"Manager, worker, gate, and handoff relationships appear as a coordinated system. The UI emphasizes explicit state transitions over chat-shaped abstraction.": "Manager、worker、gate 与 handoff 以协同系统出现；界面优先表达明确的状态迁移，而不是把一切塞进聊天框。",
	"CHANGELOG / PRODUCT EVOLUTION": "更新记录 / 产品演进",
	"Runtime evolution": "运行时演进",
	"Product changes remain visible inside the shared scene while long-form reference material stays in the semantic documentation application.": "产品变化继续呈现在共享场景中，而长篇参考资料保留在语义化文档应用里。",
	"OPEN STUDIO": "打开 STUDIO",
	"EXPLORE SYSTEM": "探索系统",
	"VIEW ARCHITECTURE": "查看架构",
	"INSPECT RUNTIME": "检查运行时",
	"VIEW AGENTS": "查看智能体",
	"OPEN PLAYGROUND": "打开实验区",
	"INSPECT STATE": "检查状态",
	"INSPECT SOURCE": "检查来源",
	"VIEW SYSTEM": "查看系统",
	"BACK TO PRODUCT": "返回产品",
	"Pinned project state and product entry boundary.": "固定的项目状态与产品入口边界。",
	"Orchestration surface coordinating context, workers, gates, and handoffs.": "协调 context、worker、gate 与 handoff 的编排界面。",
	"Sparse working context assembled for the current execution surface.": "为当前执行界面组装的稀疏工作上下文。",
	"Execution surface producing a candidate from explicit inputs and mode constraints.": "依据明确输入与 mode 约束生成 candidate 的执行界面。",
	"Specialized execution roles exposed as observable participants in the run.": "以可观测参与者形式暴露的专门执行角色。",
	"Verification boundary evaluating a candidate before downstream acceptance.": "在下游接受前评估 candidate 的验证边界。",
	"Read-only projection surface for state, receipts, and runtime evidence.": "面向 state、receipt 与 runtime evidence 的只读投影界面。",
	"Controlled boundary that separates accepted state from transient candidates.": "把 accepted state 与临时 candidate 分开的受控边界。",
	"Derived output surface rendered from accepted upstream state.": "从已接受的上游状态渲染出的派生输出界面。"
}

var _host: Control
var _window = null
var _document = null
var _locale := LOCALE_EN
var _toggle: Button
var _reverse: Dictionary = {}
var _browser_locale_callback = null

func _ready() -> void:
	_host = get_parent() as Control
	for english in ZH:
		_reverse[ZH[english]] = english

	if OS.has_feature("web"):
		_window = JavaScriptBridge.get_interface("window")
		_document = JavaScriptBridge.get_interface("document")
		var saved := ""
		if _window != null and _window.localStorage != null:
			var stored = _window.localStorage.getItem(STORAGE_KEY)
			if stored != null:
				saved = str(stored)
		if saved == LOCALE_EN or saved == LOCALE_ZH:
			_locale = saved
		else:
			var navigator = JavaScriptBridge.get_interface("navigator")
			if navigator != null and str(navigator.language).to_lower().begins_with("zh"):
				_locale = LOCALE_ZH

		_browser_locale_callback = JavaScriptBridge.create_callback(_set_locale_from_browser)
		_window.__novelforgeSetLocale = _browser_locale_callback

	call_deferred("_install")

func _install() -> void:
	if not is_instance_valid(_host):
		return
	_install_toggle()
	_replace_docs_handler()
	_hook_product_controls()
	if not _host.resized.is_connected(_on_host_resized):
		_host.resized.connect(_on_host_resized)
	apply_current_locale()
	var accessibility_bridge = _host.get_node_or_null("AccessibilityBridge")
	if accessibility_bridge != null and accessibility_bridge.has_method("_refresh_controls"):
		accessibility_bridge.call_deferred("_refresh_controls")

func _install_toggle() -> void:
	if is_instance_valid(_toggle):
		return
	var docs_button = _host.get("_docs_button")
	if not (docs_button is Button):
		return
	_toggle = Button.new()
	_toggle.name = "LocaleToggle"
	_toggle.custom_minimum_size = Vector2(64, 44)
	_toggle.add_theme_font_size_override("font_size", 9)
	_toggle.add_theme_color_override("font_color", Color("b8c5d8"))
	_toggle.add_theme_color_override("font_hover_color", Color("eef4fb"))
	_toggle.add_theme_stylebox_override("normal", _button_style(Color(0.035, 0.05, 0.08, 0.72), Color(0.22, 0.31, 0.45, 0.46)))
	_toggle.add_theme_stylebox_override("hover", _button_style(Color(0.07, 0.10, 0.15, 0.90), Color(0.32, 0.42, 0.58, 0.65)))
	_toggle.set_meta("novelforge_locale_hooked", true)
	_toggle.pressed.connect(_toggle_locale)
	var row := docs_button.get_parent()
	row.add_child(_toggle)
	row.move_child(_toggle, docs_button.get_index())

func _replace_docs_handler() -> void:
	var docs_button = _host.get("_docs_button")
	if not (docs_button is Button):
		return
	for connection in docs_button.pressed.get_connections():
		var callable: Callable = connection["callable"]
		if docs_button.pressed.is_connected(callable):
			docs_button.pressed.disconnect(callable)
	docs_button.pressed.connect(_open_docs)

func _hook_product_controls() -> void:
	_hook_buttons_recursive(_host)
	var map = _host.get("_map")
	if map != null and map.has_signal("node_selected") and not map.has_meta("novelforge_locale_hooked"):
		map.set_meta("novelforge_locale_hooked", true)
		map.node_selected.connect(Callable(self, "_after_product_interaction").unbind(1))

func _hook_buttons_recursive(node: Node) -> void:
	if node is Button and node != _toggle and not node.has_meta("novelforge_locale_hooked"):
		node.set_meta("novelforge_locale_hooked", true)
		node.pressed.connect(_after_product_interaction)
	for child in node.get_children():
		_hook_buttons_recursive(child)

func _after_product_interaction() -> void:
	call_deferred("apply_current_locale")

func _on_host_resized() -> void:
	call_deferred("apply_current_locale")

func _toggle_locale() -> void:
	_set_locale(LOCALE_EN if _locale == LOCALE_ZH else LOCALE_ZH)

func _set_locale(locale: String) -> void:
	_locale = LOCALE_ZH if locale == LOCALE_ZH else LOCALE_EN
	if _window != null and _window.localStorage != null:
		_window.localStorage.setItem(STORAGE_KEY, _locale)
	apply_current_locale()

func _set_locale_from_browser(args: Array) -> void:
	if args.size() > 0:
		_set_locale(str(args[0]))

func apply_current_locale() -> void:
	if not is_instance_valid(_host):
		return
	var translated := _apply_node(_host)
	_hook_product_controls()
	if is_instance_valid(_toggle):
		_toggle.text = "EN" if _locale == LOCALE_ZH else "中文"
		_toggle.tooltip_text = "Switch to English" if _locale == LOCALE_ZH else "切换到简体中文"
	_publish_locale(translated)

func _apply_node(node: Node) -> int:
	var count := 0
	if node is Label or node is Button:
		var current := str(node.text)
		var had_arrow := current.ends_with("  →")
		var english := _english_form(current)
		if ZH.has(english):
			var next := str(ZH[english]) if _locale == LOCALE_ZH else english
			if had_arrow:
				next += "  →"
			node.text = next
			count += 1
	for child in node.get_children():
		count += _apply_node(child)
	return count

func _english_form(text: String) -> String:
	var base := text.trim_suffix("  →") if text.ends_with("  →") else text
	return str(_reverse.get(base, base))

func _open_docs() -> void:
	var target := "/docs/en/" if _locale == LOCALE_EN else "/docs/"
	if _window != null:
		_window.location.assign(target)
	else:
		print("Docs: %s" % target)

func _publish_locale(translated_count: int) -> void:
	if _document == null:
		return
	_document.documentElement.lang = "zh-CN" if _locale == LOCALE_ZH else "en"
	_document.documentElement.dataset.novelforgeLocale = _locale
	_document.documentElement.dataset.novelforgeLocaleApplied = str(translated_count)
	_document.documentElement.dataset.novelforgeDocsRoot = "/docs/" if _locale == LOCALE_ZH else "/docs/en/"

func _button_style(bg: Color, border: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.border_width_left = 1
	style.border_width_right = 1
	style.border_width_top = 1
	style.border_width_bottom = 1
	style.corner_radius_top_left = 9
	style.corner_radius_top_right = 9
	style.corner_radius_bottom_left = 9
	style.corner_radius_bottom_right = 9
	return style
