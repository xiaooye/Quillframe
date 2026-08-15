extends Control

signal node_selected(node_id: String)

const BG := Color("0a0e17")
const GRID := Color("172033")
const GRID_FINE := Color("111827")
const EDGE := Color("33415c")
const EDGE_HOT := Color("4ee1c1")
const TEXT := Color("e7edf7")
const MUTED := Color("7d8ba5")
const PANEL := Color("101725")
const PANEL_HOT := Color("15263a")
const ACCENT := Color("73f1d1")
const SHADOW := Color(0.0, 0.0, 0.0, 0.35)

const NODES := [
	{"id": "project", "label": "PROJECT", "p": [0.10, 0.48], "phone": [0.18, 0.12], "depth": 0.35},
	{"id": "manager", "label": "MANAGER", "p": [0.28, 0.48], "phone": [0.50, 0.20], "depth": 0.55},
	{"id": "context", "label": "CONTEXT", "p": [0.47, 0.28], "phone": [0.22, 0.35], "depth": 0.85},
	{"id": "worker", "label": "WORKER", "p": [0.47, 0.68], "phone": [0.74, 0.35], "depth": 0.75},
	{"id": "agents", "label": "AGENTS", "p": [0.67, 0.18], "phone": [0.16, 0.54], "depth": 1.05},
	{"id": "gate", "label": "GATE", "p": [0.67, 0.48], "phone": [0.50, 0.54], "depth": 1.10},
	{"id": "inspector", "label": "INSPECT", "p": [0.67, 0.78], "phone": [0.84, 0.54], "depth": 0.95},
	{"id": "settlement", "label": "SETTLE", "p": [0.84, 0.48], "phone": [0.50, 0.73], "depth": 1.25},
	{"id": "publication", "label": "PUBLISH", "p": [0.93, 0.68], "phone": [0.74, 0.87], "depth": 1.35},
]

const EDGES := [
	["project", "manager"],
	["manager", "context"],
	["manager", "worker"],
	["context", "agents"],
	["context", "gate"],
	["worker", "gate"],
	["worker", "inspector"],
	["gate", "settlement"],
	["inspector", "settlement"],
	["settlement", "publication"],
]

const ROUTE_FOCUS := {
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

var _time := 0.0
var _parallax := Vector2.ZERO
var _hovered := ""
var _focus := "project"
var _selected := "project"
var _layout_mode := "desktop"

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_process(true)

func set_focus(route: String) -> void:
	_focus = str(ROUTE_FOCUS.get(route, "project"))
	queue_redraw()

func set_layout_mode(mode: String) -> void:
	_layout_mode = mode
	queue_redraw()

func _process(delta: float) -> void:
	_time += delta
	if size.x > 0.0 and size.y > 0.0:
		var center := size * 0.5
		var mouse := get_local_mouse_position()
		var strength := 8.0 if _is_phone() else 22.0
		var target := (mouse - center) / maxf(size.x, size.y) * strength
		_parallax = _parallax.lerp(target, minf(1.0, delta * 5.5))
	queue_redraw()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_hovered = _node_at(event.position)
		queue_redraw()
	elif event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
			var hit := _node_at(event.position)
			if not hit.is_empty():
				_selected = hit
				node_selected.emit(hit)
				queue_redraw()
				accept_event()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BG, true)
	_draw_grid(42.0 if _is_phone() else 56.0, GRID_FINE, _parallax * 0.18)
	_draw_grid(126.0 if _is_phone() else 168.0, GRID, _parallax * 0.34)

	for edge in EDGES:
		var from_id := str(edge[0])
		var to_id := str(edge[1])
		var a := _node_center(from_id)
		var b := _node_center(to_id)
		var hot := from_id == _focus or to_id == _focus or from_id == _selected or to_id == _selected
		var color := EDGE_HOT if hot else EDGE
		draw_line(a, b, color, 2.0 if hot else 1.0, true)
		_draw_packet(a, b, from_id, to_id, hot)

	for node in NODES:
		_draw_node(node)

	var font := get_theme_default_font()
	var footer_text := "LIVE SYSTEM MAP  ·  PORTRAIT CONTROL" if _is_phone() else "LIVE SYSTEM MAP  ·  SPATIAL RUNTIME"
	draw_string(font, Vector2(16 if _is_phone() else 24, size.y - 16 if _is_phone() else size.y - 24), footer_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 9 if _is_phone() else 12, MUTED)

func _draw_grid(step: float, color: Color, offset: Vector2) -> void:
	if step <= 0.0:
		return
	var x := fmod(offset.x, step)
	while x < size.x:
		draw_line(Vector2(x, 0), Vector2(x, size.y), color, 1.0)
		x += step
	var y := fmod(offset.y, step)
	while y < size.y:
		draw_line(Vector2(0, y), Vector2(size.x, y), color, 1.0)
		y += step

func _draw_packet(a: Vector2, b: Vector2, from_id: String, to_id: String, hot: bool) -> void:
	var seed := float(abs((from_id + to_id).hash()) % 1000) / 1000.0
	var t := fmod(_time * (0.16 if hot else 0.09) + seed, 1.0)
	var p := a.lerp(b, t)
	var glow := ACCENT if hot else Color("4b617d")
	var outer_radius := 4.5 if _is_phone() and hot else (5.5 if hot else 3.0)
	draw_circle(p, outer_radius, Color(glow.r, glow.g, glow.b, 0.14))
	draw_circle(p, 1.8 if _is_phone() else (2.1 if hot else 1.4), glow)

func _draw_node(node: Dictionary) -> void:
	var id := str(node["id"])
	var label := str(node["label"])
	var rect := _node_rect(node)
	var is_hot := id == _focus or id == _selected or id == _hovered
	var depth := float(node["depth"])
	var lift := Vector2(3.0, 4.0) * depth if _is_phone() else Vector2(5.0, 7.0) * depth
	var shadow_rect := Rect2(rect.position + lift, rect.size)
	draw_rect(shadow_rect, SHADOW, true)
	draw_rect(rect, PANEL_HOT if is_hot else PANEL, true)
	draw_rect(rect, ACCENT if is_hot else EDGE, false, 1.5 if is_hot else 1.0)

	var port_x := 9.0 if _is_phone() else 14.0
	var port := Vector2(rect.position.x + port_x, rect.get_center().y)
	draw_circle(port, 3.0 if _is_phone() else 4.0, ACCENT if is_hot else MUTED)
	if is_hot:
		draw_circle(port, 7.0 if _is_phone() else 9.0, Color(ACCENT.r, ACCENT.g, ACCENT.b, 0.08))

	var font := get_theme_default_font()
	var text_color := TEXT if is_hot else Color("b3bfd2")
	if _is_phone():
		draw_string(font, Vector2(rect.position.x + 18.0, rect.position.y + 27.0), label, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 24.0, 10, text_color)
	else:
		draw_string(font, Vector2(rect.position.x + 28.0, rect.position.y + 27.0), label, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 38.0, 13, text_color)
		draw_string(font, Vector2(rect.position.x + 28.0, rect.position.y + 45.0), id.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 38.0, 9, MUTED)

func _node_rect(node: Dictionary) -> Rect2:
	var key := "phone" if _is_phone() else "p"
	var p_data: Array = node[key]
	var normalized := Vector2(float(p_data[0]), float(p_data[1]))
	var depth := float(node["depth"])
	var center := Vector2(normalized.x * size.x, normalized.y * size.y) + _parallax * depth
	if _is_phone():
		var phone_width := clampf(size.x * 0.21, 72.0, 96.0)
		return Rect2(center - Vector2(phone_width, 44.0) * 0.5, Vector2(phone_width, 44.0))
	var width := clampf(size.x * 0.13, 116.0, 172.0)
	return Rect2(center - Vector2(width, 58.0) * 0.5, Vector2(width, 58.0))

func _node_center(id: String) -> Vector2:
	for node in NODES:
		if str(node["id"]) == id:
			return _node_rect(node).get_center()
	return Vector2.ZERO

func _node_at(position: Vector2) -> String:
	for index in range(NODES.size() - 1, -1, -1):
		var node: Dictionary = NODES[index]
		if _node_rect(node).grow(5.0 if _is_phone() else 4.0).has_point(position):
			return str(node["id"])
	return ""

func _is_phone() -> bool:
	return _layout_mode == "phone"
