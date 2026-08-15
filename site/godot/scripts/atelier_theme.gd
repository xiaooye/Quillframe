extends RefCounted

# Godot projection of the established Story Loom Kawaii Atelier v5 visual grammar.
# All chroma derives from the canonical generated Story Loom token projection.
const Story = preload("res://generated/story_loom_tokens.gd")

const EXPERIENCE := "story-loom-kawaii-atelier-v5"

static func paper() -> Color:
	return Story.NEUTRAL_FILL

static func paper_warm() -> Color:
	return Story.NEUTRAL_FILL.lerp(Story.EVIDENCE_FILL, 0.38)

static func paper_pink() -> Color:
	return Story.NEUTRAL_FILL.lerp(Story.EDITORIAL_FILL, 0.46)

static func paper_blue() -> Color:
	return Story.NEUTRAL_FILL.lerp(Story.PROJECT_FILL, 0.46)

static func paper_violet() -> Color:
	return Story.NEUTRAL_FILL.lerp(Story.RUNTIME_FILL, 0.46)

static func paper_mint() -> Color:
	return Story.NEUTRAL_FILL.lerp(Story.VALIDATED_FILL, 0.46)

static func paper_rose() -> Color:
	return Story.NEUTRAL_FILL.lerp(Story.REJECTED_FILL, 0.46)

static func ink() -> Color:
	return Story.NEUTRAL.darkened(0.48)

static func ink_soft() -> Color:
	return Story.NEUTRAL.darkened(0.16)

static func pencil() -> Color:
	return Story.NEUTRAL

static func line(alpha: float = 1.0) -> Color:
	var value := Story.RUNTIME_FILL.lerp(Story.RUNTIME, 0.23)
	return Color(value.r, value.g, value.b, alpha)

static func stitch(alpha: float = 1.0) -> Color:
	var value := Story.RUNTIME_FILL.lerp(Story.RUNTIME, 0.38)
	return Color(value.r, value.g, value.b, alpha)

static func shadow(alpha: float = 0.10) -> Color:
	return Color(0.25, 0.17, 0.30, alpha)

static func fill_for(accent: Color) -> Color:
	if _same_rgb(accent, Story.PROJECT): return paper_blue()
	if _same_rgb(accent, Story.RUNTIME): return paper_violet()
	if _same_rgb(accent, Story.EDITORIAL): return paper_pink()
	if _same_rgb(accent, Story.EVIDENCE): return paper_warm()
	if _same_rgb(accent, Story.VALIDATED): return paper_mint()
	if _same_rgb(accent, Story.REJECTED): return paper_rose()
	return paper()

static func soft(accent: Color, amount: float = 0.20) -> Color:
	return paper().lerp(fill_for(accent), clampf(amount * 2.2, 0.0, 1.0))

static func style(bg: Color, border: Color, radius: int = 22, border_width: int = 1, shadow_size: int = 0, shadow_offset: Vector2 = Vector2(0, 3)) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = bg
	box.border_color = border
	box.border_width_left = border_width
	box.border_width_right = border_width
	box.border_width_top = border_width
	box.border_width_bottom = border_width
	box.corner_radius_top_left = radius
	box.corner_radius_top_right = radius
	box.corner_radius_bottom_left = max(6, radius - 8)
	box.corner_radius_bottom_right = radius
	if shadow_size > 0:
		box.shadow_color = shadow(0.10)
		box.shadow_size = shadow_size
		box.shadow_offset = shadow_offset
	return box

static func _same_rgb(a: Color, b: Color) -> bool:
	return absf(a.r - b.r) < 0.012 and absf(a.g - b.g) < 0.012 and absf(a.b - b.b) < 0.012
