extends Control

const Story = preload("res://generated/story_loom_tokens.gd")
const Atelier = preload("res://scripts/atelier_theme.gd")
var _accent := Story.PROJECT

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_process(false)

func set_accent(color: Color) -> void:
	_accent = color
	queue_redraw()

func set_reduced_motion(_enabled: bool) -> void:
	set_process(false)
	queue_redraw()

func _draw() -> void:
	# Story Loom Kawaii Atelier v5: warm paper first, soft lane chroma second.
	draw_rect(Rect2(Vector2.ZERO, size), Atelier.paper(), true)
	_draw_grid(32.0, Atelier.line(0.16))
	var short_side := minf(size.x, size.y)
	_draw_soft_orb(Vector2(size.x * 0.12, size.y * 0.06), short_side * 0.54, Story.PROJECT_FILL, 0.34)
	_draw_soft_orb(Vector2(size.x * 0.91, size.y * 0.10), short_side * 0.58, Story.EDITORIAL_FILL, 0.30)
	_draw_soft_orb(Vector2(size.x * 0.58, size.y * 0.92), short_side * 0.50, Story.RUNTIME_FILL, 0.22)
	_draw_soft_orb(Vector2(size.x * 0.48, size.y * 0.34), short_side * 0.22, Atelier.fill_for(_accent), 0.16)
	_draw_confetti()
	draw_rect(Rect2(Vector2.ZERO, size), Atelier.line(0.30), false, 1.0)

func _draw_grid(step: float, color: Color) -> void:
	if step <= 0.0: return
	var x := 0.0
	while x < size.x:
		draw_line(Vector2(x, 0), Vector2(x, size.y), color, 1.0)
		x += step
	var y := 0.0
	while y < size.y:
		draw_line(Vector2(0, y), Vector2(size.x, y), color, 1.0)
		y += step

func _draw_soft_orb(center: Vector2, radius: float, color: Color, alpha: float) -> void:
	if radius <= 0.0: return
	for index in range(12, 0, -1):
		var ratio := float(index) / 12.0
		var layer_alpha := alpha * (1.0 - ratio * 0.70) / 5.0
		draw_circle(center, radius * ratio, Color(color.r, color.g, color.b, layer_alpha))

func _draw_confetti() -> void:
	var marks := [
		[Vector2(0.065, 0.22), Story.EDITORIAL, 4.0],
		[Vector2(0.92, 0.34), Story.PROJECT, 3.0],
		[Vector2(0.82, 0.76), Story.EVIDENCE, 3.5],
		[Vector2(0.18, 0.82), Story.VALIDATED, 3.0],
	]
	for mark in marks:
		var p := Vector2(size.x * float(mark[0].x), size.y * float(mark[0].y))
		var c: Color = mark[1]
		var r := float(mark[2])
		draw_circle(p, r, Color(c.r, c.g, c.b, 0.22))
		draw_line(p - Vector2(r * 1.8, 0), p + Vector2(r * 1.8, 0), Color(c.r, c.g, c.b, 0.18), 1.0)
		draw_line(p - Vector2(0, r * 1.8), p + Vector2(0, r * 1.8), Color(c.r, c.g, c.b, 0.18), 1.0)
