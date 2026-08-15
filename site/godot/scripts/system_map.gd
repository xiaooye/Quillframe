extends Control

signal node_selected(node_id: String)

const BG := Color("090e17")
const GRID := Color(0.25, 0.36, 0.54, 0.095)
const GRID_FINE := Color(0.18, 0.27, 0.42, 0.055)
const EDGE := Color("34425b")
const TEXT := Color("eef4fb")
const SOFT := Color("b9c6d8")
const MUTED := Color("71819b")
const PANEL := Color("0d1522")
const PANEL_HOT := Color("122235")
const SHADOW := Color(0.0, 0.0, 0.0, 0.42)

const NODES := [
	{"id": "project", "label": "PROJECT", "meta": "ROOT", "p": [0.10, 0.48], "phone": [0.18, 0.12], "depth": 0.35},
	{"id": "manager", "label": "MANAGER", "meta": "CONTROL", "p": [0.28, 0.48], "phone": [0.50, 0.20], "depth": 0.55},
	{"id": "context", "label": "CONTEXT", "meta": "INPUT", "p": [0.47, 0.28], "phone": [0.22, 0.35], "depth": 0.85},
	{"id": "worker", "label": "WORKER", "meta": "EXEC", "p": [0.47, 0.68], "phone": [0.74, 0.35], "depth": 0.75},
	{"id": "agents", "label": "AGENTS", "meta": "POOL", "p": [0.67, 0.18], "phone": [0.16, 0.54], "depth": 1.05},
	{"id": "gate", "label": "GATE", "meta": "VERIFY", "p": [0.67, 0.48], "phone": [0.50, 0.54], "depth": 1.10},
	{"id": "inspector", "label": "INSPECT", "meta": "OBSERVE", "p": [0.67, 0.78], "phone": [0.84, 0.54], "depth": 0.95},
	{"id": "settlement", "label": "SETTLE", "meta": "COMMIT", "p": [0.84, 0.48], "phone": [0.50, 0.73], "depth": 1.25},
	{"id": "publication", "label": "PUBLISH", "meta": "DERIVE", "p": [0.93, 0.68], "phone": [0.74, 0.87], "depth": 1.35},
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

var _time := 0.0
var _parallax := Vector2.ZERO
var _hovered := ""
var _focus := "project"
var _selected := "project"
var _route := "/"
var _accent := Color("73f1d1")
var _layout_mode := "desktop"

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_process(true)

func set_focus(route: String) -> void:
	_route = route
	_focus = str(ROUTE_FOCUS.get(route, "project"))
	_accent = ROUTE_ACCENTS.get(route, Color("73f1d1"))
	queue_redraw()

func set_layout_mode(mode: String) -> void:
	_layout_mode = mode
	queue_redraw()

func _process(delta: float) -> void:
	_time += delta
	if size.x > 0.0 and size.y > 0.0:
		var center := size * 0.5
		var mouse := get_local_mouse_position()
		var strength := 7.0 if _is_phone() else 20.0
		var target := (mouse - center) / maxf(size.x, size.y) * strength
		_parallax = _parallax.lerp(target, minf(1.0, delta * 4.4))
	queue_redraw()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var next_hovered := _node_at(event.position)
		if next_hovered != _hovered:
			_hovered = next_hovered
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
	_draw_atmosphere()
	_draw_grid(40.0 if _is_phone() else 52.0, GRID_FINE, _parallax * 0.16)
	_draw_grid(160.0 if _is_phone() else 208.0, GRID, _parallax * 0.30)
	_draw_regions()

	for edge in EDGES:
		var from_id := str(edge[0])
		var to_id := str(edge[1])
		var a := _node_center(from_id)
		var b := _node_center(to_id)
		var hot := from_id == _focus or to_id == _focus or from_id == _selected or to_id == _selected
		_draw_edge(a, b, from_id, to_id, hot)

	for node in NODES:
		_draw_node(node)

	_draw_screen_chrome()

func _draw_atmosphere() -> void:
	var short_side := minf(size.x, size.y)
	var pulse := (sin(_time * 0.55) + 1.0) * 0.5
	for index in range(7, 0, -1):
		var ratio := float(index) / 7.0
		var alpha := (0.005 + pulse * 0.0018) * (1.0 - ratio * 0.55)
		draw_circle(Vector2(size.x * 0.58, size.y * 0.48) + _parallax * 0.3, short_side * 0.58 * ratio, Color(_accent.r, _accent.g, _accent.b, alpha))

func _draw_regions() -> void:
	if _is_phone():
		return
	var font := get_theme_default_font()
	var label_color := Color(MUTED.r, MUTED.g, MUTED.b, 0.72)
	var regions := [
		{"x": 0.03, "w": 0.30, "label": "ORCHESTRATION"},
		{"x": 0.35, "w": 0.38, "label": "EXECUTION + VERIFICATION"},
		{"x": 0.75, "w": 0.22, "label": "SETTLEMENT"},
	]
	for region in regions:
		var rect := Rect2(Vector2(size.x * float(region["x"]), 52), Vector2(size.x * float(region["w"]), size.y - 104))
		draw_rect(rect, Color(0.10, 0.15, 0.24, 0.10), true)
		draw_rect(rect, Color(0.27, 0.37, 0.53, 0.12), false, 1.0)
		draw_string(font, rect.position + Vector2(12, 21), str(region["label"]), HORIZONTAL_ALIGNMENT_LEFT, -1, 9, label_color)

func _draw_edge(a: Vector2, b: Vector2, from_id: String, to_id: String, hot: bool) -> void:
	var curve := _curve_points(a, b)
	var line_color := _accent if hot else EDGE
	if hot:
		draw_polyline(curve, Color(_accent.r, _accent.g, _accent.b, 0.11), 7.0 if not _is_phone() else 5.0, true)
	draw_polyline(curve, Color(line_color.r, line_color.g, line_color.b, 0.92 if hot else 0.72), 1.8 if hot else 1.0, true)
	_draw_packet(curve, from_id, to_id, hot)

func _curve_points(a: Vector2, b: Vector2) -> PackedVector2Array:
	var points := PackedVector2Array()
	var horizontal := absf(b.x - a.x) >= absf(b.y - a.y)
	var bend := maxf(34.0, minf(120.0, a.distance_to(b) * 0.34))
	var c1 := a + (Vector2(bend if b.x >= a.x else -bend, 0) if horizontal else Vector2(0, bend if b.y >= a.y else -bend))
	var c2 := b - (Vector2(bend if b.x >= a.x else -bend, 0) if horizontal else Vector2(0, bend if b.y >= a.y else -bend))
	for index in range(21):
		var t := float(index) / 20.0
		var u := 1.0 - t
		points.append(a * u * u * u + c1 * 3.0 * u * u * t + c2 * 3.0 * u * t * t + b * t * t * t)
	return points

func _draw_packet(curve: PackedVector2Array, from_id: String, to_id: String, hot: bool) -> void:
	if curve.size() < 2:
		return
	var seed := float(abs((from_id + to_id).hash()) % 1000) / 1000.0
	var count := 2 if hot else 1
	for packet_index in range(count):
		var phase := fmod(_time * (0.18 if hot else 0.085) + seed + float(packet_index) * 0.48, 1.0)
		var scaled := phase * float(curve.size() - 1)
		var index := mini(int(floor(scaled)), curve.size() - 2)
		var local_t := scaled - float(index)
		var p := curve[index].lerp(curve[index + 1], local_t)
		var glow := _accent if hot else Color("526983")
		draw_circle(p, 6.0 if hot else 3.5, Color(glow.r, glow.g, glow.b, 0.10))
		draw_circle(p, 2.1 if hot else 1.4, glow)

func _draw_node(node: Dictionary) -> void:
	var id := str(node["id"])
	var label := str(node["label"])
	var meta := str(node["meta"])
	var base_rect := _node_rect(node)
	var is_focus := id == _focus
	var is_selected := id == _selected
	var is_hovered := id == _hovered
	var is_hot := is_focus or is_selected or is_hovered
	var rect := base_rect.grow(2.5 if is_hovered and not _is_phone() else 0.0)
	var depth := float(node["depth"])
	var lift := Vector2(2.0, 3.0) * depth if _is_phone() else Vector2(5.0, 7.0) * depth
	var shadow_rect := Rect2(rect.position + lift, rect.size)

	draw_rect(shadow_rect, SHADOW, true)
	if is_hot:
		draw_rect(rect.grow(5.0), Color(_accent.r, _accent.g, _accent.b, 0.045), true)
	draw_rect(rect, PANEL_HOT if is_hot else PANEL, true)
	draw_rect(rect, Color(_accent.r, _accent.g, _accent.b, 0.88) if is_hot else Color(0.27, 0.35, 0.48, 0.76), false, 1.5 if is_hot else 1.0)

	var rail_x := rect.position.x + 1.0
	draw_line(Vector2(rail_x, rect.position.y + 8), Vector2(rail_x, rect.end.y - 8), Color(_accent.r, _accent.g, _accent.b, 0.94 if is_hot else 0.26), 2.0)
	var port := Vector2(rect.position.x + (11.0 if _is_phone() else 15.0), rect.get_center().y)
	draw_circle(port, 3.0 if _is_phone() else 3.6, _accent if is_hot else MUTED)
	if is_selected:
		var pulse := 7.5 + sin(_time * 4.0) * 1.2
		draw_circle(port, pulse, Color(_accent.r, _accent.g, _accent.b, 0.065))

	var font := get_theme_default_font()
	var text_color := TEXT if is_hot else SOFT
	if _is_phone():
		draw_string(font, Vector2(rect.position.x + 19.0, rect.position.y + 27.0), label, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 23.0, 10, text_color)
	else:
		draw_string(font, Vector2(rect.position.x + 30.0, rect.position.y + 25.0), label, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 38.0, 13, text_color)
		draw_string(font, Vector2(rect.position.x + 30.0, rect.position.y + 43.0), meta, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 38.0, 8, _accent if is_hot else MUTED)

func _draw_screen_chrome() -> void:
	var font := get_theme_default_font()
	var top_y := 24.0 if _is_phone() else 29.0
	var side := 14.0 if _is_phone() else 22.0
	var route_label := _route.to_upper()
	if route_label == "/":
		route_label = "/PRODUCT"
	draw_string(font, Vector2(side, top_y), "FLOW FIELD", HORIZONTAL_ALIGNMENT_LEFT, -1, 10 if _is_phone() else 11, _accent)
	var right_text := "%s  ·  %s" % [route_label, _focus.to_upper()]
	var right_width := 210.0 if _is_phone() else 320.0
	draw_string(font, Vector2(maxf(side, size.x - right_width - side), top_y), right_text, HORIZONTAL_ALIGNMENT_RIGHT, right_width, 8 if _is_phone() else 9, MUTED)

	var bottom_y := size.y - (13.0 if _is_phone() else 18.0)
	var footer_text := "TAP NODES · ROUTES STAY LIVE" if _is_phone() else "INTERACTIVE TOPOLOGY  ·  SELECT A NODE TO BIND THE INSPECTOR"
	draw_string(font, Vector2(side, bottom_y), footer_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 8 if _is_phone() else 9, MUTED)

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

func _node_rect(node: Dictionary) -> Rect2:
	var key := "phone" if _is_phone() else "p"
	var p_data: Array = node[key]
	var normalized := Vector2(float(p_data[0]), float(p_data[1]))
	var depth := float(node["depth"])
	var center := Vector2(normalized.x * size.x, normalized.y * size.y) + _parallax * depth
	if _is_phone():
		var phone_width := clampf(size.x * 0.22, 74.0, 98.0)
		return Rect2(center - Vector2(phone_width, 44.0) * 0.5, Vector2(phone_width, 44.0))
	var width := clampf(size.x * 0.135, 120.0, 176.0)
	return Rect2(center - Vector2(width, 58.0) * 0.5, Vector2(width, 58.0))

func _node_center(id: String) -> Vector2:
	for node in NODES:
		if str(node["id"]) == id:
			return _node_rect(node).get_center()
	return Vector2.ZERO

func _node_at(position: Vector2) -> String:
	for index in range(NODES.size() - 1, -1, -1):
		var node: Dictionary = NODES[index]
		if _node_rect(node).grow(6.0 if _is_phone() else 5.0).has_point(position):
			return str(node["id"])
	return ""

func _is_phone() -> bool:
	return _layout_mode == "phone"
