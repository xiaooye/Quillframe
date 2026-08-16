extends "res://scripts/visual_completion.gd"

# Adaptive runtime completion layer.
#
# The route surfaces deliberately retain parity-calibrated art direction, but
# much of that geometry is derived from the live Control width. Rebuilding only
# when the high-level phone/compact/desktop topology changes leaves stale widths
# during continuous browser resizing inside a topology. Coalesce resize events
# to one deferred rebuild, preserve the user's vertical context, and expose a
# deterministic browser marker so CI can prove same-topology reflow happened.

var _resize_rebuild_queued := false
var _last_built_viewport_size := Vector2.ZERO
var _responsive_revision := 0

func _ready() -> void:
	_last_built_viewport_size = size
	super._ready()
	_last_built_viewport_size = size
	_publish_responsive_state()

func _on_viewport_changed() -> void:
	if _resize_rebuild_queued:
		return
	_resize_rebuild_queued = true
	call_deferred("_rebuild_for_viewport")

func _rebuild_for_viewport() -> void:
	_resize_rebuild_queued = false
	var next_size := size
	if next_size.is_equal_approx(_last_built_viewport_size):
		return

	var previous_scroll := 0
	if _scroll != null:
		previous_scroll = _scroll.scroll_vertical

	_last_built_viewport_size = next_size
	_build()
	_responsive_revision += 1
	_publish_ready()
	_publish_responsive_state()
	call_deferred("_restore_scroll_position", previous_scroll)

func _restore_scroll_position(previous_scroll: int) -> void:
	if _scroll == null:
		return
	_scroll.scroll_vertical = previous_scroll

func _publish_responsive_state() -> void:
	_set_dataset("novelforgeResponsive", "ready")
	_set_dataset("novelforgeResponsiveRevision", str(_responsive_revision))
	_set_dataset("novelforgeResponsiveLayout", _layout)
	_set_dataset("novelforgeResponsiveWidth", str(roundi(size.x)))
