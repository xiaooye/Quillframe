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
	var short_side := minf(size.x, size.y)
	_draw_soft_orb(Vector2(size.x * 0.10, size.y * 0.08), short_side * 0.56, Story.EDITORIAL, 0.055)
	_draw_soft_orb(Vector2(size.x * 0.88, size.y * 0.12), short_side * 0.48, Story.RUNTIME, 0.048)
	_draw_soft_orb(Vector2(size.x * 0.74, size.y * 0.84), short_side * 0.44, Story.PROJECT, 0.030)
	_draw_soft_orb(Vector2(size.x * 0.18, size.y * 0.76), short_side * 0.36, Story.EVIDENCE, 0.026)
	# Paper grain without turning the page into a HUD grid.
	var y := 18.0
	while y < size.y:
		draw_line(Vector2(0, y), Vector2(size.x, y), Color(Story.BORDER.r, Story.BORDER.g, Story.BORDER.b, 0.020), 1.0)
		y += 36.0

func _draw_soft_orb(center: Vector2, radius: float, color: Color, alpha: float) -> void:
	if radius <= 0.0: return
	for index in range(12, 0, -1):
		var ratio := float(index) / 12.0
		var layer_alpha := alpha * (1.0 - ratio * 0.72) / 3.4
		draw_circle(center, radius * ratio, Color(color.r, color.g, color.b, layer_alpha))
