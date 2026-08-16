extends "res://scripts/geometry_parity.gd"

# Browser/product interaction parity. No polling loop: browser-originated events
# enter Godot through retained JavaScriptBridge callbacks.

const COMMAND_ITEMS := [
	["⌂", "Home", "NovelForge product entry", "/"],
	["♡", "Product", "Product model and mechanism boundaries", "/product"],
	["✦", "Studio", "Creative workbench and hosted Studio handoff", "/studio"],
	["⌘", "Architecture", "Execution path and subsystem ownership", "/architecture"],
	["✧", "Publication", "Accepted manuscript to deterministic derivatives", "/publication"],
	["▣", "Inspect project", "Browser-local Project manifest and lock inspection", "/inspect"],
	["▷", "Playground", "Local deterministic execution trace", "/playground"],
	["◈", "Agent integration", "Portable Agent Skill and Host Bridge", "/agents"],
	["○", "Changelog", "Current implementation truth", "/changelog"],
	["📚", "Knowledge", "Search and read NovelForge documentation", "/docs"],
	["✦", "Hosted Studio", "Open studio.novelforge.wei-dev.com", "external:studio"],
]

var _dark := false
var _web_window
var _web_key_callback
var _web_popstate_callback
var _command_overlay: Control
var _command_query := ""
var _command_index := 0
var _mobile_menu: Control

func _ready() -> void:
	_dark = _initial_dark()
	super._ready()
	_install_browser_hooks()
	_sync_document_state()
	_set_dataset("novelforgeInteraction", "ready")

func _build() -> void:
	_command_overlay = null
	_mobile_menu = null
	super._build()
	_wire_interactions()

func _initial_dark() -> bool:
	if not OS.has_feature("web"):
		return false
	var value = JavaScriptBridge.eval("(() => { const saved=localStorage.getItem('novelforge.appearance'); if(saved==='dark') return true; if(saved==='light') return false; return matchMedia('(prefers-color-scheme: dark)').matches; })()")
	return bool(value) if typeof(value) == TYPE_BOOL else false

func _install_browser_hooks() -> void:
	if not OS.has_feature("web"):
		return
	_web_window = JavaScriptBridge.get_interface("window")
	if _web_window == null:
		return
	_web_key_callback = JavaScriptBridge.create_callback(_on_web_keydown)
	_web_popstate_callback = JavaScriptBridge.create_callback(_on_web_popstate)
	_web_window.addEventListener("keydown", _web_key_callback)
	_web_window.addEventListener("popstate", _web_popstate_callback)

func _exit_tree() -> void:
	if OS.has_feature("web") and _web_window != null:
		if _web_key_callback != null:
			_web_window.removeEventListener("keydown", _web_key_callback)
		if _web_popstate_callback != null:
			_web_window.removeEventListener("popstate", _web_popstate_callback)

func _wire_interactions() -> void:
	var theme := _find_button_exact(self, "◐")
	if theme == null:
		theme = _find_button_exact(self, "☼")
	if theme != null:
		theme.text = "☼" if _dark else "◐"
		theme.add_theme_font_override("font", _mixed_font(650))
		if not theme.pressed.is_connected(_toggle_appearance):
			theme.pressed.connect(_toggle_appearance)

	var menu := _find_button_exact(self, "≡")
	if menu != null and not menu.pressed.is_connected(_toggle_mobile_menu):
		menu.pressed.connect(_toggle_mobile_menu)

	_wire_search_surface("⌕  Search NovelForge")
	_wire_search_surface("⌕  Search product")
	_wire_search_surface("⌕  搜索")
	_localize_header()

func _wire_search_surface(prefix: String) -> void:
	var label := _find_label_prefix(self, prefix)
	if label == null or not (label.get_parent() is Control):
		return
	var surface := label.get_parent() as Control
	surface.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	surface.mouse_filter = Control.MOUSE_FILTER_STOP
	if not surface.gui_input.is_connected(_on_search_surface_input):
		surface.gui_input.connect(_on_search_surface_input)

func _localize_header() -> void:
	if _locale != "zh-CN":
		return
	var replacements := {
		"Product": "产品",
		"Architecture": "架构",
		"Publication": "出版",
		"Docs": "知识库",
		"✦ Open Studio": "✦ 打开 Studio",
	}
	for source_label in replacements.keys():
		var button := _find_button_exact(self, str(source_label))
		if button != null:
			button.text = str(replacements[source_label])
	var search := _find_label_prefix(self, "⌕  Search NovelForge")
	if search != null:
		search.text = "⌕  搜索 NovelForge"

func _on_search_surface_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_open_command_palette()
		get_viewport().set_input_as_handled()

func _on_web_keydown(args: Array) -> void:
	if args.is_empty():
		return
	var event = args[0]
	var key := str(event.key)
	var shortcut := (bool(event.ctrlKey) or bool(event.metaKey)) and key.to_lower() == "k"
	if shortcut:
		event.preventDefault()
		_open_command_palette()
		return
	if not _command_open():
		return
	match key:
		"Escape":
			event.preventDefault()
			_close_command_palette()
		"Backspace":
			event.preventDefault()
			if not _command_query.is_empty():
				_command_query = _command_query.left(_command_query.length() - 1)
				_command_index = 0
				_render_command_palette()
		"ArrowDown":
			event.preventDefault()
			var results := _filtered_command_items()
			if not results.is_empty():
				_command_index = min(_command_index + 1, results.size() - 1)
				_render_command_palette()
		"ArrowUp":
			event.preventDefault()
			_command_index = max(_command_index - 1, 0)
			_render_command_palette()
		"Enter":
			event.preventDefault()
			var results := _filtered_command_items()
			if _command_index < results.size():
				_run_command(str(results[_command_index][3]))
		_:
			if key.length() == 1 and not bool(event.ctrlKey) and not bool(event.metaKey) and not bool(event.altKey):
				event.preventDefault()
				_command_query += key
				_command_index = 0
				_render_command_palette()

func _on_web_popstate(_args: Array) -> void:
	_close_command_palette()
	_close_mobile_menu()
	_build()
	_publish_ready()
	_sync_document_state()

func _toggle_appearance() -> void:
	_dark = not _dark
	_sync_document_state()
	var button := _find_button_exact(self, "◐")
	if button == null:
		button = _find_button_exact(self, "☼")
	if button != null:
		button.text = "☼" if _dark else "◐"
		button.add_theme_font_override("font", _mixed_font(650))

func _toggle_locale() -> void:
	super._toggle_locale()
	_sync_document_state()

func _navigate(path: String) -> void:
	var target := path
	if path == "/docs" and _locale == "en-US":
		target = "/docs/en"
	_close_command_palette()
	_close_mobile_menu()
	super._navigate(target)
	_sync_document_state()

func _sync_document_state() -> void:
	if not OS.has_feature("web"):
		return
	var appearance := "dark" if _dark else "light"
	var lang := "zh-CN" if _locale == "zh-CN" else "en"
	JavaScriptBridge.eval("document.documentElement.lang='%s'; document.documentElement.dataset.locale='%s'; document.documentElement.dataset.novelforgeAppearance='%s'; localStorage.setItem('novelforge.locale','%s'); localStorage.setItem('novelforge.appearance','%s');" % [lang, _locale, appearance, _locale, appearance])

func _set_dataset(key: String, value: String) -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("document.documentElement.dataset.%s='%s';" % [key, value])

func _command_open() -> bool:
	return _command_overlay != null and is_instance_valid(_command_overlay)

func _open_command_palette() -> void:
	_close_mobile_menu()
	if _command_open():
		return
	_command_query = ""
	_command_index = 0
	_command_overlay = Control.new()
	_command_overlay.name = "CommandPalette"
	_command_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_command_overlay.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_command_overlay)
	_set_dataset("novelforgeCommand", "open")
	_set_dataset("novelforgeCommandQuery", "")
	_render_command_palette()

func _render_command_palette() -> void:
	if not _command_open():
		return
	for child in _command_overlay.get_children():
		_command_overlay.remove_child(child)
		child.free()
	_set_dataset("novelforgeCommandQuery", _command_query)
	var shade := ColorRect.new()
	shade.color = Color(0.12, 0.08, 0.16, 0.22)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_STOP
	shade.gui_input.connect(_on_command_shade_input)
	_command_overlay.add_child(shade)
	var phone: bool = _layout == "phone"
	var surface_width: float = minf(size.x - (24.0 if phone else 80.0), 680.0)
	var surface_height: float = minf(size.y - (40.0 if phone else 100.0), 620.0)
	var surface_x: float = (size.x - surface_width) / 2.0
	var surface_y: float = 18.0 if phone else 70.0
	var surface := _panel(Vector2(surface_x, surface_y), Vector2(surface_width, surface_height), Color("fffdfc"), 22, Color("d8cae8"), 1, Color(0.18,0.12,0.24,0.18), 18)
	_command_overlay.add_child(surface)
	var cute := _mixed_label("✦  Search NovelForge    Weave something lovely today (｡•̀ᴗ-)✧", 12, 650, C.editorial)
	cute.position = Vector2(22, 18)
	cute.size = Vector2(surface_width - 44, 24)
	surface.add_child(cute)
	var input := _panel(Vector2(20, 52), Vector2(surface_width - 40, 52), Color("fffaf7"), 13, Color("ead6c7"), 1)
	surface.add_child(input)
	var placeholder := "搜索产品、文档、架构、出版…" if _locale == "zh-CN" else "Search product, docs, architecture, publication…"
	var query_text := "⌕  " + (_command_query if not _command_query.is_empty() else placeholder)
	var query := _mixed_label(query_text, 15, 480, C.ink if not _command_query.is_empty() else C.muted)
	query.position = Vector2(15, 14)
	query.size = Vector2(input.size.x - 95, 24)
	input.add_child(query)
	input.add_child(_pill("Esc", Vector2(input.size.x - 66, 13), Vector2(48, 26), C.surface_soft, C.muted, 10, 600))
	var results := _filtered_command_items()
	var y := 118.0
	var available_rows := int((surface_height - y - 18.0) / 52.0)
	for i in range(min(results.size(), available_rows)):
		var item = results[i]
		var active := i == _command_index
		var bg := C.runtime_soft if active else Color(0,0,0,0)
		var button := _mixed_text_button("%s  %s" % [str(item[0]), str(item[1])], Vector2(20, y), Vector2(surface_width - 40, 46), bg, C.runtime if active else C.ink, 14, 620, 11)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.pressed.connect(_run_command.bind(str(item[3])))
		surface.add_child(button)
		y += 52.0

func _filtered_command_items() -> Array:
	var q := _command_query.strip_edges().to_lower()
	if q.is_empty():
		return COMMAND_ITEMS.duplicate()
	var results := []
	for item in COMMAND_ITEMS:
		var haystack := (str(item[1]) + " " + str(item[2])).to_lower()
		if haystack.contains(q):
			results.append(item)
	return results

func _run_command(target: String) -> void:
	if target == "external:studio":
		_close_command_palette()
		_open_external(STUDIO_URL)
		return
	_navigate(target)

func _on_command_shade_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_close_command_palette()

func _close_command_palette() -> void:
	if _command_open():
		_command_overlay.queue_free()
	_command_overlay = null
	_set_dataset("novelforgeCommand", "closed")
	_set_dataset("novelforgeCommandQuery", "")

func _toggle_mobile_menu() -> void:
	if _mobile_menu != null and is_instance_valid(_mobile_menu):
		_close_mobile_menu()
		return
	_close_command_palette()
	_mobile_menu = Control.new()
	_mobile_menu.name = "MobileMenu"
	_mobile_menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_mobile_menu.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_mobile_menu)
	_set_dataset("novelforgeMobileMenu", "open")
	var width: float = minf(size.x - 24.0, 360.0)
	var surface := _panel(Vector2(size.x - width - 12.0, 72.0), Vector2(width, 506.0), Color("fffdfc"), 18, Color("d8cae8"), 1, Color(0.18,0.12,0.24,0.16), 16)
	_mobile_menu.add_child(surface)
	var search_text := "⌕  搜索 NovelForge" if _locale == "zh-CN" else "⌕  Search NovelForge"
	var search := _mixed_text_button(search_text, Vector2(12, 12), Vector2(width - 24, 48), C.surface_soft, C.runtime, 14, 620, 12)
	search.pressed.connect(_open_command_palette)
	surface.add_child(search)
	var routes := [["产品" if _locale == "zh-CN" else "Product", "/product"], ["Studio", "/studio"], ["架构" if _locale == "zh-CN" else "Architecture", "/architecture"], ["出版" if _locale == "zh-CN" else "Publication", "/publication"], ["知识库" if _locale == "zh-CN" else "Knowledge", "/docs"], ["检查项目" if _locale == "zh-CN" else "Inspect", "/inspect"], ["Playground", "/playground"], ["Agent 集成" if _locale == "zh-CN" else "Agents", "/agents"], ["更新日志" if _locale == "zh-CN" else "Changelog", "/changelog"]]
	var y := 68.0
	for item in routes:
		var button := _text_button(str(item[0]), Vector2(12, y), Vector2(width - 24, 42), Color(0,0,0,0), C.ink, 13, 600, 10)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.pressed.connect(_navigate.bind(str(item[1])))
		surface.add_child(button)
		y += 46.0

func _close_mobile_menu() -> void:
	if _mobile_menu != null and is_instance_valid(_mobile_menu):
		_mobile_menu.queue_free()
	_mobile_menu = null
	_set_dataset("novelforgeMobileMenu", "closed")
