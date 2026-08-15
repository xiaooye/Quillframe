extends Node

const Story = preload("res://generated/story_loom_tokens.gd")
const MIN_TARGET := Story.MIN_TOUCH_TARGET

var _host: Control
var _document = null
var _reduced_motion := false

func _ready() -> void:
	_host = get_parent() as Control
	if OS.has_feature("web"):
		_document = JavaScriptBridge.get_interface("document")
		_reduced_motion = bool(JavaScriptBridge.eval("window.matchMedia('(prefers-reduced-motion: reduce)').matches"))
	call_deferred("_install")

func _install() -> void:
	if not is_instance_valid(_host): return
	_apply_controls(_host)
	_apply_motion_preference()
	if not _host.resized.is_connected(_on_host_resized): _host.resized.connect(_on_host_resized)
	_publish_state()

func _on_host_resized() -> void: call_deferred("_refresh_controls")

func _refresh_controls() -> void:
	if is_instance_valid(_host):
		_apply_controls(_host)
		_publish_state()

func _apply_controls(node: Node) -> void:
	if node is Button:
		node.focus_mode = Control.FOCUS_ALL
		node.custom_minimum_size = Vector2(maxf(node.custom_minimum_size.x, MIN_TARGET), maxf(node.custom_minimum_size.y, MIN_TARGET))
		node.add_theme_stylebox_override("focus", _focus_style())
	for child in node.get_children(): _apply_controls(child)

func _apply_motion_preference() -> void:
	for property_name in ["_map", "_backdrop"]:
		var surface = _host.get(property_name)
		if surface != null and surface.has_method("set_reduced_motion"): surface.set_reduced_motion(_reduced_motion)

func _publish_state() -> void:
	if _document == null: return
	_document.documentElement.dataset.novelforgeA11y = "ready"
	_document.documentElement.dataset.novelforgeTarget = str(int(MIN_TARGET))
	_document.documentElement.dataset.novelforgeMotion = "reduced" if _reduced_motion else "bounded"

func _focus_style() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Story.SURFACE_OVERLAY
	style.border_color = Story.RING
	var width := int(Story.FOCUS_RING_WIDTH)
	style.border_width_left = width; style.border_width_right = width; style.border_width_top = width; style.border_width_bottom = width
	style.corner_radius_top_left = int(Story.RADIUS_SM); style.corner_radius_top_right = int(Story.RADIUS_SM)
	style.corner_radius_bottom_left = int(Story.RADIUS_SM); style.corner_radius_bottom_right = int(Story.RADIUS_SM)
	return style
