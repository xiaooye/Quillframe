extends Control

const BASE := Color("060911")
const GRID_FINE := Color(0.18, 0.27, 0.40, 0.09)
const GRID_MAJOR := Color(0.22, 0.34, 0.52, 0.11)
const SECONDARY := Color("8b7cff")

var _accent := Color("73f1d1")
var _time := 0.0
var _parallax := Vector2.ZERO

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_process(true)

func set_accent(color: Color) -> void:
	_accent = color
	queue_redraw()

func _process(delta: float) -> void:
	_time += delta
	if size.x > 0.0 and size.y > 0.0:
		var center := size * 0.5
		var mouse := get_local_mouse_position()
		var target := (mouse - center) / maxf(size.x, size.y) * 24.0
		_parallax = _parallax.lerp(target, minf(1.0, delta * 2.8))
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BASE, true)
	_draw_grid(36.0, GRID_FINE, _parallax * 0.10)
	_draw_grid(144.0, GRID_MAJOR, _parallax * 0.18)

	var short_side := minf(size.x, size.y)
	_draw_soft_orb(Vector2(size.x * 0.22, size.y * 0.20) + _parallax * 0.55, short_side * 0.46, _accent, 0.052)
	_draw_soft_orb(Vector2(size.x * 0.83, size.y * 0.32) - _parallax * 0.38, short_side * 0.38, SECONDARY, 0.040)
	_draw_soft_orb(Vector2(size.x * 0.60, size.y * 0.92) + Vector2(sin(_time * 0.22), cos(_time * 0.18)) * 18.0, short_side * 0.42, _accent, 0.026)

	# Quiet horizon and edge treatment keep the scene dimensional without turning
	# the product surface into a game HUD.
	var horizon_y := size.y * 0.68
	draw_line(Vector2(0, horizon_y), Vector2(size.x, horizon_y), Color(_accent.r, _accent.g, _accent.b, 0.055), 1.0)
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.25, 0.39, 0.58, 0.14), false, 1.0)

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

func _draw_soft_orb(center: Vector2, radius: float, color: Color, alpha: float) -> void:
	if radius <= 0.0:
		return
	for index in range(12, 0, -1):
		var ratio := float(index) / 12.0
		var layer_alpha := alpha * (1.0 - ratio * 0.72) / 3.6
		draw_circle(center, radius * ratio, Color(color.r, color.g, color.b, layer_alpha))
