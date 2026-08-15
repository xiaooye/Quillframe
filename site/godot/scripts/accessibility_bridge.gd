extends Node

const MIN_TARGET := 44.0

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
	if not is_instance_valid(_host):
		return
	_apply_controls(_host)
	_apply_motion_preference()
	if not _host.resized.is_connected(_on_host_resized):
		_host.resized.connect(_on_host_resized)
	_publish_state()

func _on_host_resized() -> void:
	call_deferred("_refresh_controls")

func _refresh_controls() -> void:
	if is_instance_valid(_host):
		_apply_controls(_host)
		_publish_state()

func _apply_controls(node: Node) -> void:
	if node is Button:
		node.focus_mode = Control.FOCUS_ALL
		node.custom_minimum_size = Vector2(maxf(node.custom_minimum_size.x, MIN_TARGET), maxf(node.custom_minimum_size.y, MIN_TARGET))
		node.add_theme_stylebox_override("focus", _focus_style())
	for child in node.get_children():
		_apply_controls(child)

func _apply_motion_preference() -> void:
	var map = _host.get("_map")
	var backdrop = _host.get("_backdrop")
	if map is Node:
		map.set_process(not _reduced_motion)
		if map is CanvasItem:
			map.queue_redraw()
	if backdrop is Node:
		backdrop.set_process(not _reduced_motion)
		if backdrop is CanvasItem:
			backdrop.queue_redraw()

func _publish_state() -> void:
	if _document == null:
		return
	_document.documentElement.dataset.novelforgeA11y = "ready"
	_document.documentElement.dataset.novelforgeTarget = "44"
	_document.documentElement.dataset.novelforgeMotion = "reduced" if _reduced_motion else "full"

func _focus_style() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.07, 0.10, 0.15, 0.96)
	style.border_color = Color("eef4fb")
	style.border_width_left = 2
	style.border_width_right = 2
	style.border_width_top = 2
	style.border_width_bottom = 2
	style.corner_radius_top_left = 9
	style.corner_radius_top_right = 9
	style.corner_radius_bottom_left = 9
	style.corner_radius_bottom_right = 9
	return style
