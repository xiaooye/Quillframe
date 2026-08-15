extends Control

signal node_selected(node_id: String)

const Story = preload("res://generated/story_loom_tokens.gd")
const Atelier = preload("res://scripts/atelier_theme.gd")

const NODES := [
	{"id": "project", "label": "PROJECT", "meta": "ROOT", "lane": "project", "p": [0.10, 0.48], "phone": [0.18, 0.12], "depth": 0.35},
	{"id": "manager", "label": "MANAGER", "meta": "CONTROL", "lane": "runtime", "p": [0.28, 0.48], "phone": [0.50, 0.20], "depth": 0.55},
	{"id": "context", "label": "CONTEXT", "meta": "INPUT", "lane": "project", "p": [0.47, 0.28], "phone": [0.22, 0.35], "depth": 0.85},
	{"id": "worker", "label": "WORKER", "meta": "EXEC", "lane": "editorial", "p": [0.47, 0.68], "phone": [0.74, 0.35], "depth": 0.75},
	{"id": "agents", "label": "AGENTS", "meta": "POOL", "lane": "validated", "p": [0.67, 0.18], "phone": [0.16, 0.54], "depth": 1.05},
	{"id": "gate", "label": "GATE", "meta": "VERIFY", "lane": "evidence", "p": [0.67, 0.48], "phone": [0.50, 0.54], "depth": 1.10},
	{"id": "inspector", "label": "INSPECT", "meta": "OBSERVE", "lane": "project", "p": [0.67, 0.78], "phone": [0.84, 0.54], "depth": 0.95},
	{"id": "settlement", "label": "SETTLE", "meta": "COMMIT", "lane": "validated", "p": [0.84, 0.48], "phone": [0.50, 0.73], "depth": 1.25},
	{"id": "publication", "label": "PUBLISH", "meta": "DERIVE", "lane": "editorial", "p": [0.93, 0.68], "phone": [0.74, 0.87], "depth": 1.35},
]

const EDGES := [
	["project", "manager"], ["manager", "context"], ["manager", "worker"],
	["context", "agents"], ["context", "gate"], ["worker", "gate"],
	["worker", "inspector"], ["gate", "settlement"], ["inspector", "settlement"],
	["settlement", "publication"],
]

const ROUTE_FOCUS := {
	"/": "project", "/start": "project", "/product": "project", "/studio": "worker",
	"/architecture": "manager", "/publication": "publication", "/inspect": "inspector",
	"/playground": "context", "/agents": "agents", "/changelog": "project",
}

const ROUTE_ACCENTS := {
	"/": Story.PROJECT, "/start": Story.PROJECT, "/product": Story.PROJECT,
	"/studio": Story.EDITORIAL, "/architecture": Story.RUNTIME, "/publication": Story.EVIDENCE,
	"/inspect": Story.PROJECT, "/playground": Story.EDITORIAL, "/agents": Story.VALIDATED,
	"/changelog": Story.NEUTRAL,
}

var _time: float = 0.0
var _motion_remaining: float = 0.0
var _parallax: Vector2 = Vector2.ZERO
var _hovered: String = ""
var _focus: String = "project"
var _selected: String = "project"
var _route: String = "/"
var _accent: Color = Story.PROJECT
var _layout_mode: String = "desktop"
var _reduced_motion: bool = false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_process(false)

func set_focus(route: String) -> void:
	_route = route
	_focus = str(ROUTE_FOCUS.get(route, "project"))
	_accent = ROUTE_ACCENTS.get(route, Story.PROJECT)
	_kick_motion(0.72)
	queue_redraw()

func select_node(node_id: String) -> void:
	_selected = node_id
	_kick_motion(0.42)
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
		var motion: InputEventMouseMotion = event
		var next_hovered: String = _node_at(motion.position)
		if next_hovered != _hovered:
			_hovered = next_hovered
			queue_redraw()
		if not _reduced_motion and size.x > 0.0 and size.y > 0.0:
			var center: Vector2 = size * 0.5
			var strength: float = 7.0 if _is_phone() else 20.0
			var target: Vector2 = (motion.position - center) / maxf(size.x, size.y) * strength
			_parallax = _parallax.lerp(target, 0.34)
			queue_redraw()
	elif event is InputEventMouseButton:
		var click: InputEventMouseButton = event
		if click.button_index == MOUSE_BUTTON_LEFT and click.pressed:
			var hit: String = _node_at(click.position)
			if not hit.is_empty():
				_selected = hit
				_kick_motion(0.52)
				node_selected.emit(hit)
				queue_redraw()
				accept_event()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Atelier.paper(), true)
	_draw_atmosphere()
	_draw_grid(40.0 if _is_phone() else 52.0, Atelier.line(0.16), _parallax * 0.16)
	_draw_grid(160.0 if _is_phone() else 208.0, Color(Story.RUNTIME.r, Story.RUNTIME.g, Story.RUNTIME.b, 0.08), _parallax * 0.30)
	_draw_regions()
	for edge in EDGES:
		var from_id: String = str(edge[0])
		var to_id: String = str(edge[1])
		var a: Vector2 = _node_center(from_id)
		var b: Vector2 = _node_center(to_id)
		var hot: bool = from_id == _focus or to_id == _focus or from_id == _selected or to_id == _selected
		_draw_edge(a, b, from_id, to_id, hot)
	for item in NODES:
		var node: Dictionary = item
		_draw_node(node)
	_draw_screen_chrome()

func _draw_atmosphere() -> void:
	var short_side: float = minf(size.x, size.y)
	var pulse: float = (sin(_time * 4.2) + 1.0) * 0.5 if _motion_remaining > 0.0 and not _reduced_motion else 0.35
	var fill: Color = Atelier.fill_for(_accent)
	for index in range(7, 0, -1):
		var ratio: float = float(index) / 7.0
		var alpha: float = (0.010 + pulse * 0.0025) * (1.0 - ratio * 0.55)
		draw_circle(Vector2(size.x * 0.58, size.y * 0.48) + _parallax * 0.3, short_side * 0.58 * ratio, Color(fill.r, fill.g, fill.b, alpha))

func _draw_regions() -> void:
	if _is_phone(): return
	var font: Font = get_theme_default_font()
	var label_color: Color = Color(Atelier.pencil().r, Atelier.pencil().g, Atelier.pencil().b, 0.78)
	var regions := [
		{"x": 0.03, "w": 0.30, "label": "ORCHESTRATION"},
		{"x": 0.35, "w": 0.38, "label": "EXECUTION + VERIFICATION"},
		{"x": 0.75, "w": 0.22, "label": "SETTLEMENT"},
	]
	for item in regions:
		var region: Dictionary = item
		var rect := Rect2(Vector2(size.x * float(region["x"]), 52), Vector2(size.x * float(region["w"]), size.y - 104))
		draw_style_box(Atelier.style(Color(Atelier.paper_violet().r, Atelier.paper_violet().g, Atelier.paper_violet().b, 0.28), Atelier.line(0.48), 18, 1), rect)
		draw_string(font, rect.position + Vector2(12, 21), str(region["label"]), HORIZONTAL_ALIGNMENT_LEFT, -1, 9, label_color)

func _draw_edge(a: Vector2, b: Vector2, from_id: String, to_id: String, hot: bool) -> void:
	var curve: PackedVector2Array = _curve_points(a, b)
	var line_color: Color = _accent if hot else Atelier.stitch(0.72)
	if hot:
		draw_polyline(curve, Color(_accent.r, _accent.g, _accent.b, 0.10), 7.0 if not _is_phone() else 5.0, true)
	draw_polyline(curve, Color(line_color.r, line_color.g, line_color.b, 0.90 if hot else 0.66), 1.8 if hot else 1.0, true)
	_draw_packet(curve, from_id, to_id, hot)

func _curve_points(a: Vector2, b: Vector2) -> PackedVector2Array:
	var points := PackedVector2Array()
	var horizontal: bool = absf(b.x - a.x) >= absf(b.y - a.y)
	var bend: float = maxf(34.0, minf(120.0, a.distance_to(b) * 0.34))
	var c1: Vector2 = a + (Vector2(bend if b.x >= a.x else -bend, 0) if horizontal else Vector2(0, bend if b.y >= a.y else -bend))
	var c2: Vector2 = b - (Vector2(bend if b.x >= a.x else -bend, 0) if horizontal else Vector2(0, bend if b.y >= a.y else -bend))
	for index in range(21):
		var t: float = float(index) / 20.0
		var u: float = 1.0 - t
		points.append(a * u * u * u + c1 * 3.0 * u * u * t + c2 * 3.0 * u * t * t + b * t * t * t)
	return points

func _draw_packet(curve: PackedVector2Array, from_id: String, to_id: String, hot: bool) -> void:
	if curve.size() < 2: return
	var seed: float = float(abs((from_id + to_id).hash()) % 1000) / 1000.0
	var count: int = 2 if hot else 1
	for packet_index in range(count):
		var phase: float = fmod(_time * (0.22 if hot else 0.10) + seed + float(packet_index) * 0.48, 1.0)
		var scaled: float = phase * float(curve.size() - 1)
		var index: int = mini(int(floor(scaled)), curve.size() - 2)
		var local_t: float = scaled - float(index)
		var p: Vector2 = curve[index].lerp(curve[index + 1], local_t)
		var glow: Color = _accent if hot else Atelier.pencil()
		draw_circle(p, 6.0 if hot else 3.5, Color(glow.r, glow.g, glow.b, 0.10))
		draw_circle(p, 2.1 if hot else 1.4, glow)

func _draw_node(node: Dictionary) -> void:
	var id: String = str(node["id"])
	var label: String = str(node["label"])
	var meta: String = str(node["meta"])
	var lane_color: Color = _lane_color(str(node["lane"]))
	var base_rect: Rect2 = _node_rect(node)
	var is_focus: bool = id == _focus
	var is_selected: bool = id == _selected
	var is_hovered: bool = id == _hovered
	var is_hot: bool = is_focus or is_selected or is_hovered
	var rect: Rect2 = base_rect.grow(2.5 if is_hovered and not _is_phone() else 0.0)
	var depth: float = float(node["depth"])
	var lift: Vector2 = Vector2(2.0, 3.0) * depth if _is_phone() else Vector2(5.0, 7.0) * depth
	var shadow_rect := Rect2(rect.position + lift, rect.size)
	draw_style_box(Atelier.style(Color(Atelier.paper().r, Atelier.paper().g, Atelier.paper().b, 0.0), Color(0, 0, 0, 0), 18 if _is_phone() else 20, 0, 2, lift), shadow_rect)
	if is_hot:
		draw_style_box(Atelier.style(Color(Atelier.fill_for(_accent).r, Atelier.fill_for(_accent).g, Atelier.fill_for(_accent).b, 0.38), Color(_accent.r, _accent.g, _accent.b, 0.12), 22, 1), rect.grow(5.0))
	var fill: Color = Atelier.fill_for(lane_color)
	var border: Color = Color((_accent if is_hot else lane_color).r, (_accent if is_hot else lane_color).g, (_accent if is_hot else lane_color).b, 0.72 if is_hot else 0.34)
	draw_style_box(Atelier.style(fill, border, 18 if _is_phone() else 20, 1), rect)
	var rail_x: float = rect.position.x + 3.0
	draw_line(Vector2(rail_x, rect.position.y + 9), Vector2(rail_x, rect.end.y - 9), Color(lane_color.r, lane_color.g, lane_color.b, 0.90 if is_hot else 0.40), 2.0)
	var port := Vector2(rect.position.x + (12.0 if _is_phone() else 16.0), rect.get_center().y)
	draw_circle(port, 3.0 if _is_phone() else 3.6, _accent if is_hot else lane_color)
	if is_selected:
		var pulse: float = 7.5 + (sin(_time * 8.0) * 1.2 if _motion_remaining > 0.0 and not _reduced_motion else 0.0)
		draw_circle(port, pulse, Color(_accent.r, _accent.g, _accent.b, 0.08))
	var font: Font = get_theme_default_font()
	var text_color: Color = Atelier.ink() if is_hot else Atelier.ink_soft()
	if _is_phone():
		draw_string(font, Vector2(rect.position.x + 20.0, rect.position.y + 27.0), label, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 24.0, 10, text_color)
	else:
		draw_string(font, Vector2(rect.position.x + 31.0, rect.position.y + 25.0), label, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 39.0, 13, text_color)
		draw_string(font, Vector2(rect.position.x + 31.0, rect.position.y + 43.0), meta, HORIZONTAL_ALIGNMENT_LEFT, rect.size.x - 39.0, 8, lane_color)

func _draw_screen_chrome() -> void:
	var font: Font = get_theme_default_font()
	var top_y: float = 24.0 if _is_phone() else 29.0
	var side: float = 14.0 if _is_phone() else 22.0
	var route_label: String = _route.to_upper()
	if route_label == "/": route_label = "/PRODUCT"
	draw_string(font, Vector2(side, top_y), "✦  FLOW FIELD", HORIZONTAL_ALIGNMENT_LEFT, -1, 10 if _is_phone() else 11, _accent)
	var right_text := "%s  ·  %s" % [route_label, _focus.to_upper()]
	var right_width: float = 210.0 if _is_phone() else 320.0
	draw_string(font, Vector2(maxf(side, size.x - right_width - side), top_y), right_text, HORIZONTAL_ALIGNMENT_RIGHT, right_width, 8 if _is_phone() else 9, Atelier.pencil())
	var bottom_y: float = size.y - (13.0 if _is_phone() else 18.0)
	var footer_text := "♡  TAP NODES · ROUTES STAY LIVE" if _is_phone() else "♡  INTERACTIVE TOPOLOGY  ·  SELECT A NODE TO BIND THE INSPECTOR"
	draw_string(font, Vector2(side, bottom_y), footer_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 8 if _is_phone() else 9, Atelier.pencil())

func _draw_grid(step: float, color: Color, offset: Vector2) -> void:
	if step <= 0.0: return
	var x: float = fmod(offset.x, step)
	while x < size.x:
		draw_line(Vector2(x, 0), Vector2(x, size.y), color, 1.0)
		x += step
	var y: float = fmod(offset.y, step)
	while y < size.y:
		draw_line(Vector2(0, y), Vector2(size.x, y), color, 1.0)
		y += step

func _node_rect(node: Dictionary) -> Rect2:
	var key: String = "phone" if _is_phone() else "p"
	var p_data: Array = node[key]
	var normalized := Vector2(float(p_data[0]), float(p_data[1]))
	var depth: float = float(node["depth"])
	var center: Vector2 = Vector2(normalized.x * size.x, normalized.y * size.y) + _parallax * depth
	if _is_phone():
		var phone_width: float = clampf(size.x * 0.22, 74.0, 98.0)
		return Rect2(center - Vector2(phone_width, 44.0) * 0.5, Vector2(phone_width, 44.0))
	var width: float = clampf(size.x * 0.135, 120.0, 176.0)
	return Rect2(center - Vector2(width, 58.0) * 0.5, Vector2(width, 58.0))

func _node_center(id: String) -> Vector2:
	for item in NODES:
		var node: Dictionary = item
		if str(node["id"]) == id: return _node_rect(node).get_center()
	return Vector2.ZERO

func _node_at(position: Vector2) -> String:
	for index in range(NODES.size() - 1, -1, -1):
		var node: Dictionary = NODES[index]
		if _node_rect(node).grow(6.0 if _is_phone() else 5.0).has_point(position): return str(node["id"])
	return ""

func _lane_color(name: String) -> Color:
	match name:
		"project": return Story.PROJECT
		"runtime": return Story.RUNTIME
		"editorial": return Story.EDITORIAL
		"evidence": return Story.EVIDENCE
		"validated": return Story.VALIDATED
		"rejected": return Story.REJECTED
		_: return Story.NEUTRAL

func _is_phone() -> bool: return _layout_mode == "phone"
