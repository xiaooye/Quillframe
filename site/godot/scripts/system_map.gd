extends Control

signal node_selected(node_id: String)

const Story = preload("res://generated/story_loom_tokens.gd")

const NODES := [
	{"id":"project","label":"PROJECT","meta":"ROOT","p":[0.24,0.18],"phone":[0.26,0.14],"fill":"project","depth":0.35},
	{"id":"manager","label":"MANAGER","meta":"CONTROL","p":[0.55,0.30],"phone":[0.70,0.25],"fill":"runtime","depth":0.55},
	{"id":"context","label":"CONTEXT","meta":"INPUT","p":[0.22,0.47],"phone":[0.24,0.40],"fill":"project","depth":0.72},
	{"id":"worker","label":"WORKER","meta":"EXEC","p":[0.50,0.47],"phone":[0.68,0.46],"fill":"runtime","depth":0.82},
	{"id":"gate","label":"GATE","meta":"VERIFY","p":[0.77,0.47],"phone":[0.28,0.62],"fill":"editorial","depth":0.96},
	{"id":"agents","label":"AGENTS","meta":"POOL","p":[0.84,0.24],"phone":[0.72,0.64],"fill":"validated","depth":0.86},
	{"id":"inspector","label":"INSPECT","meta":"READ","p":[0.84,0.67],"phone":[0.26,0.80],"fill":"evidence","depth":0.92},
	{"id":"settlement","label":"SETTLEMENT","meta":"COMMIT","p":[0.48,0.68],"phone":[0.70,0.82],"fill":"runtime","depth":1.08},
	{"id":"publication","label":"PUBLICATION","meta":"DERIVE","p":[0.48,0.86],"phone":[0.50,0.94],"fill":"validated","depth":1.18},
]

const EDGES := [
	["project","manager"],["project","context"],["context","worker"],["worker","gate"],
	["manager","gate"],["agents","gate"],["gate","settlement"],["worker","settlement"],
	["inspector","settlement"],["settlement","publication"],
]

const ROUTE_FOCUS := {
	"/":"project","/start":"project","/product":"project","/studio":"worker",
	"/architecture":"manager","/publication":"publication","/inspect":"inspector",
	"/playground":"context","/agents":"agents","/changelog":"project",
}

var _time := 0.0
var _motion_remaining := 0.0
var _parallax := Vector2.ZERO
var _hovered := ""
var _focus := "project"
var _selected := "project"
var _route := "/"
var _layout_mode := "desktop"
var _reduced_motion := false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_process(false)

func set_focus(route: String) -> void:
	_route = route
	_focus = str(ROUTE_FOCUS.get(route, "project"))
	_kick_motion(0.55)
	queue_redraw()

func select_node(node_id: String) -> void:
	_selected = node_id
	_kick_motion(0.38)
	queue_redraw()

func set_layout_mode(mode: String) -> void:
	_layout_mode = mode
	queue_redraw()

func set_reduced_motion(enabled: bool) -> void:
	_reduced_motion = enabled
	if enabled:
		_motion_remaining = 0.0
		_parallax = Vector2.ZERO
		set_process(false)
	queue_redraw()

func _kick_motion(seconds: float) -> void:
	if _reduced_motion: return
	_motion_remaining = maxf(_motion_remaining, seconds)
	set_process(true)

func _process(delta: float) -> void:
	if _reduced_motion or _motion_remaining <= 0.0:
		set_process(false)
		return
	_time += delta
	_motion_remaining -= delta
	queue_redraw()
	if _motion_remaining <= 0.0:
		_motion_remaining = 0.0
		set_process(false)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var next_hovered := _node_at(event.position)
		if next_hovered != _hovered:
			_hovered = next_hovered
			queue_redraw()
		if not _reduced_motion and size.x > 0.0 and size.y > 0.0:
			var center := size * 0.5
			var strength := 4.0 if _is_phone() else 9.0
			var target: Vector2 = (event.position - center) / maxf(size.x, size.y) * strength
			_parallax = _parallax.lerp(target, 0.28)
			queue_redraw()
	elif event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
			var hit := _node_at(event.position)
			if not hit.is_empty():
				_selected = hit
				_kick_motion(0.45)
				node_selected.emit(hit)
				queue_redraw()
				accept_event()

func _draw() -> void:
	_draw_paper_decor()
	for edge in EDGES:
		var from_id := str(edge[0])
		var to_id := str(edge[1])
		var hot := from_id == _focus or to_id == _focus or from_id == _selected or to_id == _selected
		_draw_edge(_node_center(from_id), _node_center(to_id), from_id, to_id, hot)
	for node in NODES:
		_draw_node(node)

func _draw_paper_decor() -> void:
	var font := get_theme_default_font()
	var pale := Color(Story.RUNTIME.r, Story.RUNTIME.g, Story.RUNTIME.b, 0.10)
	draw_circle(Vector2(size.x * 0.10, size.y * 0.18), 34.0, Color(Story.PROJECT.r, Story.PROJECT.g, Story.PROJECT.b, 0.07))
	draw_circle(Vector2(size.x * 0.90, size.y * 0.12), 48.0, Color(Story.EDITORIAL.r, Story.EDITORIAL.g, Story.EDITORIAL.b, 0.07))
	draw_circle(Vector2(size.x * 0.90, size.y * 0.88), 62.0, Color(Story.VALIDATED.r, Story.VALIDATED.g, Story.VALIDATED.b, 0.05))
	if not _is_phone():
		draw_string(font, Vector2(size.x * 0.08, size.y * 0.10), "STORY LOOM", HORIZONTAL_ALIGNMENT_LEFT, -1, 9, Story.RUNTIME)
		draw_string(font, Vector2(size.x * 0.76, size.y * 0.92), "authority-aware", HORIZONTAL_ALIGNMENT_LEFT, -1, 8, Story.MUTED_FOREGROUND)
	for index in range(7):
		var x := size.x * (0.12 + float(index) * 0.12)
		var y := size.y * (0.08 + float(index % 3) * 0.04)
		draw_circle(Vector2(x, y), 2.0, pale)

func _draw_edge(a: Vector2, b: Vector2, from_id: String, to_id: String, hot: bool) -> void:
	var curve := _curve_points(a, b)
	var line := Story.RUNTIME if hot else Story.BORDER
	if hot:
		draw_polyline(curve, Color(line.r, line.g, line.b, 0.10), 7.0, true)
	draw_polyline(curve, Color(line.r, line.g, line.b, 0.72 if hot else 0.84), 2.0 if hot else 1.2, true)
	_draw_packet(curve, from_id, to_id, hot)

func _curve_points(a: Vector2, b: Vector2) -> PackedVector2Array:
	var points := PackedVector2Array()
	var mid_y := (a.y + b.y) * 0.5
	var c1 := Vector2(a.x, mid_y)
	var c2 := Vector2(b.x, mid_y)
	for index in range(17):
		var t := float(index) / 16.0
		var u := 1.0 - t
		points.append(a * u * u * u + c1 * 3.0 * u * u * t + c2 * 3.0 * u * t * t + b * t * t * t)
	return points

func _draw_packet(curve: PackedVector2Array, from_id: String, to_id: String, hot: bool) -> void:
	if curve.size() < 2: return
	var phase := fmod(_time * (0.30 if hot else 0.14) + float(abs((from_id + to_id).hash()) % 100) / 100.0, 1.0)
	var scaled := phase * float(curve.size() - 1)
	var index := mini(int(floor(scaled)), curve.size() - 2)
	var p := curve[index].lerp(curve[index + 1], scaled - float(index))
	var color := Story.EDITORIAL if hot else Story.RUNTIME
	draw_circle(p, 4.5 if hot else 2.5, Color(color.r, color.g, color.b, 0.16))
	draw_circle(p, 1.8 if hot else 1.2, color)

func _draw_node(node: Dictionary) -> void:
	var id := str(node["id"])
	var rect := _node_rect(node)
	var hot := id == _focus or id == _selected or id == _hovered
	var fill := _fill_color(str(node["fill"]))
	var stroke := _stroke_color(str(node["fill"]))
	var lift := Vector2(3.0, 4.0) * float(node["depth"])
	draw_rect(Rect2(rect.position + lift, rect.size), Color(0.20, 0.12, 0.25, 0.07), true)
	if hot:
		draw_rect(rect.grow(4.0), Color(stroke.r, stroke.g, stroke.b, 0.08), true)
	draw_rect(rect, fill, true)
	draw_rect(rect, Color(stroke.r, stroke.g, stroke.b, 0.72 if hot else 0.38), false, 1.5 if hot else 1.0)
	var font := get_theme_default_font()
	var label := str(node["label"])
	var meta := str(node["meta"])
	draw_string(font, rect.position + Vector2(12, 21), label, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 24, 10 if _is_phone() else 11, Story.FOREGROUND)
	if not _is_phone():
		draw_string(font, rect.position + Vector2(12, 37), meta, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 24, 8, stroke)

func _fill_color(name: String) -> Color:
	match name:
		"project": return Story.PROJECT_FILL
		"runtime": return Story.RUNTIME_FILL
		"editorial": return Story.EDITORIAL_FILL
		"evidence": return Story.EVIDENCE_FILL
		"validated": return Story.VALIDATED_FILL
		_: return Story.NEUTRAL_FILL

func _stroke_color(name: String) -> Color:
	match name:
		"project": return Story.PROJECT
		"runtime": return Story.RUNTIME
		"editorial": return Story.EDITORIAL
		"evidence": return Story.EVIDENCE
		"validated": return Story.VALIDATED
		_: return Story.NEUTRAL

func _node_rect(node: Dictionary) -> Rect2:
	var key := "phone" if _is_phone() else "p"
	var p_data: Array = node[key]
	var center := Vector2(float(p_data[0]) * size.x, float(p_data[1]) * size.y) + _parallax * float(node["depth"])
	var width := clampf(size.x * (0.30 if _is_phone() else 0.20), 92.0, 150.0)
	var height := 42.0 if _is_phone() else 48.0
	return Rect2(center - Vector2(width, height) * 0.5, Vector2(width, height))

func _node_center(id: String) -> Vector2:
	for node in NODES:
		if str(node["id"]) == id:
			return _node_rect(node).get_center()
	return Vector2.ZERO

func _node_at(position: Vector2) -> String:
	for index in range(NODES.size() - 1, -1, -1):
		var node: Dictionary = NODES[index]
		if _node_rect(node).grow(5.0).has_point(position):
			return str(node["id"])
	return ""

func _is_phone() -> bool:
	return _layout_mode == "phone"
