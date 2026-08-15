extends Control

const Story = preload("res://generated/story_loom_tokens.gd")
const BASE := Story.BACKGROUND
const SECONDARY := Story.EDITORIAL
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
	draw_rect(Rect2(Vector2.ZERO, size), BASE, true)
	_draw_grid(36.0, Color(Story.BORDER.r, Story.BORDER.g, Story.BORDER.b, 0.055))
	_draw_grid(144.0, Color(Story.RUNTIME.r, Story.RUNTIME.g, Story.RUNTIME.b, 0.065))
	var short_side := minf(size.x, size.y)
	_draw_soft_orb(Vector2(size.x * 0.22, size.y * 0.20), short_side * 0.46, _accent, 0.052)
	_draw_soft_orb(Vector2(size.x * 0.83, size.y * 0.32), short_side * 0.38, SECONDARY, 0.040)
	_draw_soft_orb(Vector2(size.x * 0.60, size.y * 0.92), short_side * 0.42, Story.RUNTIME, 0.030)
	var horizon_y := size.y * 0.68
	draw_line(Vector2(0, horizon_y), Vector2(size.x, horizon_y), Color(_accent.r, _accent.g, _accent.b, 0.055), 1.0)
	draw_rect(Rect2(Vector2.ZERO, size), Color(Story.BORDER.r, Story.BORDER.g, Story.BORDER.b, 0.26), false, 1.0)

func _draw_grid(step: float, color: Color) -> void:
	if step <= 0.0: return
	var x := 0.0
	while x < size.x:
		draw_line(Vector2(x, 0), Vector2(x, size.y), color, 1.0); x += step
	var y := 0.0
	while y < size.y:
		draw_line(Vector2(0, y), Vector2(size.x, y), color, 1.0); y += step

func _draw_soft_orb(center: Vector2, radius: float, color: Color, alpha: float) -> void:
	if radius <= 0.0: return
	for index in range(12, 0, -1):
		var ratio := float(index) / 12.0
		var layer_alpha := alpha * (1.0 - ratio * 0.72) / 3.6
		draw_circle(center, radius * ratio, Color(color.r, color.g, color.b, layer_alpha))
