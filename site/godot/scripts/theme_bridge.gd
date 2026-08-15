extends Node

const Story = preload("res://generated/story_loom_tokens.gd")
const Atelier = preload("res://scripts/atelier_theme.gd")

const OLD_TEXT := Color("eef4fb")
const OLD_MUTED := Color("73839d")
const OLD_SOFT := Color("b8c5d8")
const OLD_BORDER := Color("233149")
const OLD_BORDER_SOFT := Color(0.22, 0.31, 0.45, 0.46)
const OLD_ACCENTS := {
	"73f1d1": "project", "7bc8ff": "editorial", "b39cff": "runtime", "ffc66e": "evidence",
	"80d4ff": "project", "f39ac7": "editorial", "a4e67d": "validated", "a8b5c9": "neutral",
}

var _host: Control
var _document = null

func _ready() -> void:
	_host = get_parent() as Control
	if OS.has_feature("web"):
		_document = JavaScriptBridge.get_interface("document")
	call_deferred("_install")

func _install() -> void:
	if not is_instance_valid(_host): return
	_hook_controls(_host)
	var map = _host.get("_map")
	if map != null and map.has_signal("node_selected") and not map.has_meta("novelforge_theme_hooked"):
		map.set_meta("novelforge_theme_hooked", true)
		map.node_selected.connect(Callable(self, "_after_interaction").unbind(1))
	if not _host.resized.is_connected(_on_host_resized): _host.resized.connect(_on_host_resized)
	apply_story_loom_theme()

func _hook_controls(node: Node) -> void:
	if node is Button and not node.has_meta("novelforge_theme_hooked"):
		node.set_meta("novelforge_theme_hooked", true)
		node.pressed.connect(_after_interaction)
	for child in node.get_children(): _hook_controls(child)

func _after_interaction() -> void: call_deferred("apply_story_loom_theme")
func _on_host_resized() -> void: call_deferred("apply_story_loom_theme")

func apply_story_loom_theme() -> void:
	if not is_instance_valid(_host): return
	_hook_controls(_host)
	var route := str(_host.get("_current_route"))
	var accent := _accent_for_route(route)
	_host.set("_accent", accent)
	var backdrop = _host.get("_backdrop")
	if backdrop != null and backdrop.has_method("set_accent"): backdrop.set_accent(accent)
	var map = _host.get("_map")
	if map != null and map.has_method("set_focus"): map.set_focus(route)
	_apply_node(_host, accent)
	_publish_theme()

func _apply_node(node: Node, accent: Color) -> void:
	if node is Control: _recolor_control(node, accent)
	for child in node.get_children(): _apply_node(child, accent)

func _recolor_control(control: Control, accent: Color) -> void:
	for color_name in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color", "separator"]:
		if control.has_theme_color_override(color_name):
			control.add_theme_color_override(color_name, _map_color(control.get_theme_color(color_name), accent))
	for style_name in ["panel", "normal", "hover", "pressed", "focus"]:
		if not control.has_theme_stylebox_override(style_name): continue
		var source := control.get_theme_stylebox(style_name)
		if source is StyleBoxFlat:
			var style: StyleBoxFlat = source.duplicate()
			style.bg_color = _map_color(style.bg_color, accent)
			style.border_color = _map_color(style.border_color, accent)
			_apply_atelier_shape(style, control)
			control.add_theme_stylebox_override(style_name, style)

func _apply_atelier_shape(style: StyleBoxFlat, control: Control) -> void:
	if control is Button:
		style.corner_radius_top_left = maxi(style.corner_radius_top_left, 14)
		style.corner_radius_top_right = maxi(style.corner_radius_top_right, 14)
		style.corner_radius_bottom_left = maxi(style.corner_radius_bottom_left, 8)
		style.corner_radius_bottom_right = maxi(style.corner_radius_bottom_right, 14)
	elif control is PanelContainer:
		style.corner_radius_top_left = maxi(style.corner_radius_top_left, 20)
		style.corner_radius_top_right = maxi(style.corner_radius_top_right, 20)
		style.corner_radius_bottom_left = maxi(style.corner_radius_bottom_left, 12)
		style.corner_radius_bottom_right = maxi(style.corner_radius_bottom_right, 20)
		if style.bg_color.a > 0.12 and style.shadow_size == 0:
			style.shadow_color = Atelier.shadow(0.085)
			style.shadow_size = 2
			style.shadow_offset = Vector2(0, 3)

func _map_color(value: Color, accent: Color) -> Color:
	if value.a <= 0.001: return value
	if _same_rgb(value, Story.BACKGROUND) or _same_rgb(value, Story.SURFACE_SUNKEN): return _with_alpha(Atelier.paper(), value.a)
	if _same_rgb(value, Story.CARD) or _same_rgb(value, Story.SURFACE_RAISED): return _with_alpha(Atelier.paper(), value.a)
	if _same_rgb(value, Story.MUTED) or _same_rgb(value, Story.SURFACE_OVERLAY): return _with_alpha(Atelier.paper_warm(), value.a)
	if _same_rgb(value, Story.FOREGROUND) or _same_rgb(value, Story.CARD_FOREGROUND): return _with_alpha(Atelier.ink(), value.a)
	if _same_rgb(value, Story.MUTED_FOREGROUND): return _with_alpha(Atelier.pencil(), value.a)
	if _same_rgb(value, Story.BORDER): return _with_alpha(Atelier.line(value.a), value.a)
	if _same_rgb(value, Story.PRIMARY) or _same_rgb(value, Story.RING): return _with_alpha(Story.RUNTIME, value.a)
	if _same_rgb(value, Story.PRIMARY_FOREGROUND): return _with_alpha(Atelier.ink(), value.a)
	for story_color in [Story.PROJECT, Story.RUNTIME, Story.EDITORIAL, Story.EVIDENCE, Story.VALIDATED, Story.REJECTED, Story.NEUTRAL]:
		if _same_rgb(value, story_color): return _with_alpha(story_color, value.a)
	if _same_rgb(value, OLD_TEXT): return _with_alpha(Atelier.ink(), value.a)
	if _same_rgb(value, OLD_MUTED) or _same_rgb(value, OLD_SOFT): return _with_alpha(Atelier.pencil(), value.a)
	if _same_rgb(value, OLD_BORDER) or _same_rgb(value, OLD_BORDER_SOFT): return _with_alpha(Atelier.line(value.a), value.a)
	var key := value.to_html(false).substr(0, 6).to_lower()
	if OLD_ACCENTS.has(key): return _with_alpha(_semantic_color(str(OLD_ACCENTS[key])), value.a)
	if _same_rgb(value, accent): return _with_alpha(accent, value.a)
	var luma := value.get_luminance()
	if luma < 0.065: return _with_alpha(Atelier.paper(), value.a)
	if luma < 0.13: return _with_alpha(Atelier.paper_warm(), value.a)
	if luma < 0.22: return _with_alpha(Atelier.paper_violet(), value.a)
	return value

func _same_rgb(a: Color, b: Color) -> bool:
	return absf(a.r - b.r) < 0.012 and absf(a.g - b.g) < 0.012 and absf(a.b - b.b) < 0.012

func _with_alpha(color: Color, alpha: float) -> Color: return Color(color.r, color.g, color.b, alpha)

func _semantic_color(name: String) -> Color:
	match name:
		"project": return Story.PROJECT
		"runtime": return Story.RUNTIME
		"editorial": return Story.EDITORIAL
		"evidence": return Story.EVIDENCE
		"validated": return Story.VALIDATED
		"rejected": return Story.REJECTED
		_: return Story.NEUTRAL

func _accent_for_route(route: String) -> Color:
	match route:
		"/studio": return Story.EDITORIAL
		"/architecture": return Story.RUNTIME
		"/publication": return Story.EVIDENCE
		"/inspect": return Story.PROJECT
		"/playground": return Story.EDITORIAL
		"/agents": return Story.VALIDATED
		"/changelog": return Story.NEUTRAL
		_: return Story.PROJECT

func _publish_theme() -> void:
	if _document == null: return
	_document.documentElement.dataset.novelforgeTheme = "story-loom-v2"
	_document.documentElement.dataset.novelforgeExperience = Atelier.EXPERIENCE
	_document.documentElement.dataset.novelforgeTokenSchema = Story.TOKEN_SCHEMA
