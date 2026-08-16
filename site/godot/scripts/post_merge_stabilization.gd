extends "res://scripts/responsive_completion.gd"

# Post-merge stabilization layer. This is intentionally bounded to runtime
# interaction evidence, deterministic decorative assets, resize coalescing,
# and the Solid page-width contract. Product semantics remain in lower layers.
const SOLID_PAGE_MAX := 1480.0
const SOLID_GUTTER_MAX := 48.0
const SOLID_INNER_MAX := SOLID_PAGE_MAX - SOLID_GUTTER_MAX * 2.0

const RIBBON_ICON_PATH := "res://assets/ribbon.svg"
const CONTEXT_ICON_PATH := "res://assets/context-bubbles.svg"
const BRAIN_ICON_PATH := "res://assets/character-brain.svg"
const PUBLICATION_ICON_PATH := "res://assets/publication-book.svg"

const AGENT_HOSTS := ["Claude Code", "Codex", "Cursor", "OpenCode", "Custom agent"]

var _ribbon_icon: Texture2D
var _context_icon: Texture2D
var _brain_icon: Texture2D
var _publication_icon: Texture2D

var _interaction_revision := 0
var _agent_host_index := 1
var _publication_hero_buttons: Array[Button] = []
var _publication_rail_buttons: Array[Button] = []
var _agent_host_buttons: Array[Button] = []
var _home_capability_buttons: Array[Button] = []

var _resize_generation := 0

func _ready() -> void:
	_ribbon_icon = load(RIBBON_ICON_PATH) as Texture2D
	_context_icon = load(CONTEXT_ICON_PATH) as Texture2D
	_brain_icon = load(BRAIN_ICON_PATH) as Texture2D
	_publication_icon = load(PUBLICATION_ICON_PATH) as Texture2D
	for required in [_ribbon_icon, _context_icon, _brain_icon, _publication_icon]:
		if required == null:
			push_error("NovelForge Godot stabilization requires bundled decorative SVG assets")
	super._ready()
	_publish_behavior_state()

func _build() -> void:
	_set_dataset("novelforgeFocusedControl", "")
	_publication_hero_buttons.clear()
	_publication_rail_buttons.clear()
	_agent_host_buttons.clear()
	_home_capability_buttons.clear()
	super._build()
	_apply_deterministic_decorations(self)
	_apply_solid_wide_page_contract()
	_wire_scroll_evidence()
	_publish_behavior_state()

# Resize storms from browser/CDP can emit several viewport sizes before the
# canvas settles. Only the latest size survives two deferred turns, so a rapid
# resize performs one tree rebuild instead of rebuilding every intermediate
# Web canvas size. This stays event-driven: no Timer and no polling loop.
func _on_viewport_changed() -> void:
	_resize_generation += 1
	call_deferred("_stabilization_resize_probe", _resize_generation, size)

func _stabilization_resize_probe(generation: int, observed: Vector2) -> void:
	if generation != _resize_generation:
		return
	if not size.is_equal_approx(observed):
		return
	call_deferred("_stabilization_resize_commit", generation, observed)

func _stabilization_resize_commit(generation: int, observed: Vector2) -> void:
	if generation != _resize_generation or not size.is_equal_approx(observed):
		return
	if size.is_equal_approx(_last_built_viewport_size):
		return
	var previous_scroll := 0
	if _scroll != null:
		previous_scroll = _scroll.scroll_vertical
	_last_built_viewport_size = size
	_build()
	_responsive_revision += 1
	_publish_ready()
	_publish_responsive_state()
	call_deferred("_restore_scroll_position", previous_scroll)

# -----------------------------------------------------------------------------
# Publication: both Solid selectors are real controls and drive one state.
# -----------------------------------------------------------------------------

func _build_format_showcase(parent: Control, pos: Vector2, showcase_size: Vector2, phone: bool) -> void:
	var showcase := _panel(pos, showcase_size, Color("fffdfc"), 20, Color(0,0,0,0), 0)
	parent.add_child(showcase)
	var profiles := _publication_profiles()
	var fills := [C.valid_soft, Color("eef8fb"), C.evidence_soft, C.editorial_soft]
	var cols := 2 if phone else 4
	var gap := 12.0
	var side_inset := 20.0 if phone else 0.0
	var card_w := (showcase_size.x - gap * (cols - 1) - side_inset) / cols
	var card_h := 300.0 if phone else 250.0
	for i in range(profiles.size()):
		var profile: Dictionary = profiles[i]
		var col := i % cols
		var row := i / cols
		var selected := i == _publication_profile
		var fill: Color = fills[i]
		var card := _panel(
			Vector2((10.0 if phone else 0.0) + col * (card_w + gap), row * (card_h + gap)),
			Vector2(card_w, card_h),
			Color("fffdfc") if i == 3 else fill,
			18,
			C.runtime if selected else Color("dbcfe2"),
			2 if selected else 1,
			Color(0.18,0.12,0.24,0.08) if selected else Color(0.18,0.12,0.24,0.05),
			7 if selected else 4
		)
		card.name = "PublicationHero%s" % str(profile["id"])
		var tag := _pill(str(profile["id"]), Vector2(10, -7), Vector2(54, 26), fill, C.runtime if selected else C.muted, 9, 720)
		card.add_child(tag)
		var page := _panel(Vector2(12, 48), Vector2(card_w - 24, card_h - 98), Color("fffdfc"), 7, Color("ded5df"), 1)
		card.add_child(page)
		var heading := _label("Chapter 1 · Nightfall…", 9, 650, C.ink)
		heading.position = Vector2(8, 24)
		heading.size = Vector2(page.size.x - 16, 24)
		page.add_child(heading)
		for j in range(4):
			var line := ColorRect.new()
			line.mouse_filter = Control.MOUSE_FILTER_IGNORE
			line.color = Color(0.25,0.22,0.28,0.16)
			line.position = Vector2(10, 62 + j * 23)
			line.size = Vector2(max(page.size.x - 30 - j * 10, 20.0), 4)
			page.add_child(line)
		var cap := _label(str(profile["label"]), 11, 520, C.runtime if selected else C.muted)
		cap.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cap.position = Vector2(0, card_h - 34)
		cap.size = Vector2(card_w, 22)
		card.add_child(cap)
		var hit := Button.new()
		hit.name = "PublicationHeroHit%s" % str(profile["id"])
		hit.text = ""
		hit.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		hit.focus_mode = Control.FOCUS_ALL
		hit.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		hit.accessibility_name = ("选择 %s 出版格式" if _locale == "zh-CN" else "Select %s publication profile") % str(profile["id"])
		hit.add_theme_stylebox_override("normal", _button_box(Color(0,0,0,0), 18))
		hit.add_theme_stylebox_override("hover", _button_box(Color(0.48,0.42,0.77,0.045), 18))
		hit.add_theme_stylebox_override("pressed", _button_box(Color(0.48,0.42,0.77,0.08), 18))
		hit.add_theme_stylebox_override("focus", _focus_box(18))
		hit.pressed.connect(_select_publication_profile.bind(i))
		hit.focus_entered.connect(_record_focus.bind(hit.name))
		card.add_child(hit)
		_publication_hero_buttons.append(hit)
		showcase.add_child(card)

func _build_format_strip(pos: Vector2, strip_size: Vector2, phone: bool) -> void:
	super._build_format_strip(pos, strip_size, phone)
	if _stage == null:
		return
	var profiles := _publication_profiles()
	for i in range(profiles.size()):
		var profile: Dictionary = profiles[i]
		var button := _find_button_prefix(_stage, str(profile["id"]))
		if button == null:
			continue
		button.name = "PublicationRail%s" % str(profile["id"])
		button.accessibility_name = ("选择 %s 出版格式" if _locale == "zh-CN" else "Select %s publication profile") % str(profile["id"])
		button.focus_entered.connect(_record_focus.bind(button.name))
		_publication_rail_buttons.append(button)

func _select_publication_profile(index: int) -> void:
	_publication_profile = clampi(index, 0, 3)
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

# -----------------------------------------------------------------------------
# Agents: match the current Solid host selector instead of hard-coding Codex.
# -----------------------------------------------------------------------------

func _build_agent_patch_bay(parent: Control, pos: Vector2, bay_size: Vector2, phone: bool) -> void:
	var bay := _panel(pos, bay_size, Color("fffdfc"), 18, Color("cfc3ee"), 1, Color(0.18,0.12,0.24,0.05), 5)
	parent.add_child(bay)
	var label := _label("AGENT PATCH BAY", 10, 760, C.runtime)
	label.position = Vector2(18, 16)
	label.size = Vector2(180, 20)
	bay.add_child(label)
	var cols := 1 if phone else 2
	var gap := 8.0
	var cell_w := bay_size.x - 36 if phone else (bay_size.x - 44) / 2.0
	var cell_h := 56.0
	for i in range(AGENT_HOSTS.size()):
		var host := str(AGENT_HOSTS[i])
		var col := i % cols
		var row := i / cols
		var selected := i == _agent_host_index
		var cell := _panel(
			Vector2(18 + col * (cell_w + gap), 44 + row * (cell_h + gap)),
			Vector2(cell_w, cell_h),
			C.runtime_soft if selected else Color("fbf9fc"),
			10,
			C.runtime if selected else Color("e5dcea"),
			2 if selected else 1
		)
		var icon_box := _panel(Vector2(12, 12), Vector2(32, 32), Color("fffdfc") if selected else C.runtime_soft, 10)
		var letter := _label("O" if host == "OpenCode" else host.left(1), 16, 760, C.runtime)
		letter.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		letter.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		letter.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		icon_box.add_child(letter)
		cell.add_child(icon_box)
		var name := _label(host, 13, 700 if selected else 650, C.runtime if selected else C.ink)
		name.position = Vector2(54, 16)
		name.size = Vector2(cell_w - 64, 24)
		cell.add_child(name)
		var hit := Button.new()
		hit.name = "AgentHost%d" % i
		hit.text = ""
		hit.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		hit.focus_mode = Control.FOCUS_ALL
		hit.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		hit.accessibility_name = ("选择 Agent 宿主 %s" if _locale == "zh-CN" else "Select agent host %s") % host
		hit.add_theme_stylebox_override("normal", _button_box(Color(0,0,0,0), 10))
		hit.add_theme_stylebox_override("hover", _button_box(Color(0.48,0.42,0.77,0.045), 10))
		hit.add_theme_stylebox_override("pressed", _button_box(Color(0.48,0.42,0.77,0.08), 10))
		hit.add_theme_stylebox_override("focus", _focus_box(10))
		hit.pressed.connect(_select_agent_host.bind(i))
		hit.focus_entered.connect(_record_focus.bind(hit.name))
		cell.add_child(hit)
		_agent_host_buttons.append(hit)
		bay.add_child(cell)
	var footer := _label("Host Bridge · authority=false", 9, 600, C.muted)
	footer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	footer.position = Vector2(18, bay_size.y - 30)
	footer.size = Vector2(bay_size.x - 36, 20)
	bay.add_child(footer)

func _build_agent_recipe(pos: Vector2, recipe_size: Vector2, phone: bool) -> void:
	super._build_agent_recipe(pos, recipe_size, phone)
	var host := str(AGENT_HOSTS[_agent_host_index])
	var english := _find_label_prefix(self, "Codex uses the same public boundary.")
	var chinese := _find_label_prefix(self, "Codex 使用同一条公开边界。")
	var title := english if english != null else chinese
	if title != null:
		title.text = ("%s 使用同一条公开边界。" if _locale == "zh-CN" else "%s uses the same public boundary.") % host

func _select_agent_host(index: int) -> void:
	_agent_host_index = clampi(index, 0, AGENT_HOSTS.size() - 1)
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

func _home_capability_chip(pos: Vector2, chip_size: Vector2, index: int, item: Dictionary) -> Panel:
	var card := super._home_capability_chip(pos, chip_size, index, item)
	for child in card.get_children():
		if child is Button:
			var hit := child as Button
			hit.name = "HomeCapability%d" % index
			hit.accessibility_name = ("选择能力 %s" if _locale == "zh-CN" else "Select capability %s") % str(item["eyebrow"])
			hit.focus_entered.connect(_record_focus.bind(hit.name))
			_home_capability_buttons.append(hit)
			break
	return card

# Keep behavior evidence in one revision counter. Lower layers own the actual
# state transitions; these overrides only record that a user-visible transition
# occurred before the same state-preserving rebuild.
func _select_home_capability(index: int) -> void:
	_interaction_revision += 1
	super._select_home_capability(index)

func _adjust_home_budget(delta: int) -> void:
	_interaction_revision += 1
	super._adjust_home_budget(delta)

func _toggle_home_gate(index: int) -> void:
	_interaction_revision += 1
	super._toggle_home_gate(index)

func _select_architecture_node(index: int) -> void:
	_interaction_revision += 1
	super._select_architecture_node(index)

func _advance_architecture_run() -> void:
	_interaction_revision += 1
	super._advance_architecture_run()

func _reset_architecture_run() -> void:
	_interaction_revision += 1
	super._reset_architecture_run()

# -----------------------------------------------------------------------------
# Deterministic decorative glyphs.
# -----------------------------------------------------------------------------

func _apply_deterministic_decorations(node: Node) -> void:
	if node is Label:
		_stabilize_label_decoration(node as Label)
	elif node is Button:
		_stabilize_button_decoration(node as Button)
	for child in node.get_children():
		_apply_deterministic_decorations(child)

func _stabilize_label_decoration(label: Label) -> void:
	var text := label.text
	if text.begins_with("🎀 "):
		label.text = text.trim_prefix("🎀 ")
		_attach_icon_before(label, _ribbon_icon)
		return
	if text == "🫧":
		_replace_label_with_icon(label, _context_icon)
		return
	if text == "🧠":
		_replace_label_with_icon(label, _brain_icon)
		return
	if text == "📖":
		_replace_label_with_icon(label, _publication_icon)
		return
	if text == "📚" or text == "📚✨":
		_replace_label_with_icon(label, _books_icon)
		return
	label.text = _replace_unsupported_decorative_text(text)

func _stabilize_button_decoration(button: Button) -> void:
	button.text = _replace_unsupported_decorative_text(button.text)

func _replace_unsupported_decorative_text(text: String) -> String:
	return text.replace("✨", "✦").replace("📚", "▤").replace("📖", "▤").replace("🧠", "◇").replace("🫧", "○").replace("🧵", "✦").replace("🎀", "").replace("🌸", "✦").replace("🛠", "⌘")

func _replace_label_with_icon(label: Label, texture: Texture2D) -> void:
	if texture == null or label.get_parent() == null:
		label.text = _replace_unsupported_decorative_text(label.text)
		return
	var rect := TextureRect.new()
	rect.name = "%sDeterministicIcon" % label.name
	rect.texture = texture
	rect.position = label.position
	rect.size = label.size
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.get_parent().add_child(rect)
	label.text = ""

func _attach_icon_before(label: Label, texture: Texture2D) -> void:
	if texture == null or label.get_parent() == null:
		return
	var icon_size := minf(maxf(label.size.y, 16.0), 22.0)
	var rect := TextureRect.new()
	rect.name = "RibbonDeterministicIcon"
	rect.texture = texture
	rect.position = label.position
	rect.size = Vector2(icon_size, icon_size)
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.get_parent().add_child(rect)
	label.position.x += icon_size + 6.0
	label.size.x = maxf(label.size.x - icon_size - 6.0, 40.0)

# -----------------------------------------------------------------------------
# Solid wide page contract.
# -----------------------------------------------------------------------------

func _apply_solid_wide_page_contract() -> void:
	if _layout != "desktop" or _stage == null:
		return
	if _solid_viewport_width() <= SOLID_PAGE_MAX:
		return
	var source_left := 70.0
	var source_width := maxf(size.x - 140.0, 1.0)
	var target_width := minf(SOLID_INNER_MAX, source_width)
	var target_left := (size.x - target_width) / 2.0
	for child in _stage.get_children():
		if not child is Control:
			continue
		var control := child as Control
		if control.anchor_left != 0.0 or control.anchor_right != 0.0:
			continue
		var local_x := control.position.x - source_left
		if local_x < -40.0 or local_x > source_width + 40.0:
			continue
		var right_inset := source_width - (local_x + control.size.x)
		if absf(local_x) <= 4.0 and absf(right_inset) <= 6.0:
			control.position.x = target_left
			_reflow_control_width(control, target_width)
		elif control is Panel and local_x > 0.0 and local_x <= 700.0 and absf(right_inset) <= 6.0:
			control.position.x = target_left + local_x
			_reflow_control_width(control, maxf(target_width - local_x, 240.0))
		elif (control is Label or control is Button) and control.size.x <= 680.0 and local_x <= 700.0:
			control.position.x = target_left + local_x
		else:
			var old_x := control.position.x
			var old_right := old_x + control.size.x
			var mapped_x := target_left + clampf(local_x / source_width, 0.0, 1.0) * target_width
			var mapped_right := target_left + clampf((old_right - source_left) / source_width, 0.0, 1.0) * target_width
			control.position.x = mapped_x
			_reflow_control_width(control, maxf(mapped_right - mapped_x, 1.0))
	_set_dataset("novelforgeWideDesktop", "solid-page-clamped")
	_set_dataset("novelforgeWideDesktopInner", str(roundi(target_width)))

func _reflow_control_width(control: Control, new_width: float) -> void:
	var old_width := control.size.x
	if old_width <= 0.0 or is_equal_approx(old_width, new_width):
		control.size.x = new_width
		return
	control.size.x = new_width
	for child in control.get_children():
		if not child is Control:
			continue
		var c := child as Control
		if c.anchor_left != 0.0 or c.anchor_right != 0.0:
			continue
		var old_x := c.position.x
		var old_right := old_x + c.size.x
		var left_inset := old_x
		var right_inset := old_width - old_right
		var preserve_fixed := (c is Label or c is Button) and c.size.x <= 680.0 and left_inset <= 80.0 and right_inset > 100.0
		var new_x := _map_bounded_coordinate(old_x, old_width, new_width)
		var new_right := _map_bounded_coordinate(old_right, old_width, new_width)
		c.position.x = new_x
		if preserve_fixed:
			continue
		var child_new_width := maxf(new_right - new_x, 1.0)
		_reflow_control_width(c, child_new_width)

func _map_bounded_coordinate(value: float, old_width: float, new_width: float) -> float:
	var edge := minf(48.0, old_width * 0.12)
	if value <= edge:
		return value
	if value >= old_width - edge:
		return new_width - (old_width - value)
	var old_inner := maxf(old_width - edge * 2.0, 1.0)
	var new_inner := maxf(new_width - edge * 2.0, 1.0)
	return edge + (value - edge) * new_inner / old_inner

func _record_focus(control_name: String) -> void:
	_set_dataset("novelforgeFocusedControl", control_name)

# -----------------------------------------------------------------------------
# Browser QA evidence. These markers are non-authoritative and intentionally
# expose state/real control rectangles rather than source-code implementation.
# -----------------------------------------------------------------------------

func _wire_scroll_evidence() -> void:
	if _scroll == null:
		return
	var bar := _scroll.get_v_scroll_bar()
	if bar != null and not bar.value_changed.is_connected(_on_scroll_evidence_changed):
		bar.value_changed.connect(_on_scroll_evidence_changed)
	_on_scroll_evidence_changed(float(_scroll.scroll_vertical))

func _on_scroll_evidence_changed(value: float) -> void:
	_set_dataset("novelforgeScrollY", str(roundi(value)))
	call_deferred("_publish_interaction_targets")

func _publish_interaction_targets() -> void:
	_publish_control_targets("novelforgePublicationHeroTargets", _publication_hero_buttons)
	_publish_control_targets("novelforgePublicationRailTargets", _publication_rail_buttons)
	_publish_control_targets("novelforgeAgentTargets", _agent_host_buttons)
	_publish_control_targets("novelforgeHomeTargets", _home_behavior_buttons())
	_publish_control_targets("novelforgeArchitectureTargets", _architecture_behavior_buttons())

func _home_behavior_buttons() -> Array[Button]:
	var result: Array[Button] = []
	for button in _home_capability_buttons:
		if button != null and is_instance_valid(button):
			result.append(button)
	for exact in ["−", "+"]:
		var button := _find_button_exact(self, exact)
		if button != null:
			button.name = "HomeBudgetMinus" if exact == "−" else "HomeBudgetPlus"
			result.append(button)
	for gate in ["Surface", "Reader", "Continuity", "Semantic"]:
		var button := _find_button_contains(self, gate)
		if button != null:
			button.name = "HomeGate%s" % gate
			result.append(button)
	return result

func _architecture_behavior_buttons() -> Array[Button]:
	var result: Array[Button] = []
	var nodes := _architecture_nodes()
	for i in range(nodes.size()):
		var button := _find_button_contains(self, str(nodes[i]["title"]))
		if button != null:
			button.name = "ArchitectureNode%d" % i
			result.append(button)
	for label in ["Simulate a run", "Next step", "模拟一次 run", "下一步"]:
		var next := _find_button_exact(self, label)
		if next != null:
			next.name = "ArchitectureNext"
			if not result.has(next):
				result.append(next)
			break
	for label in ["Reset", "重置"]:
		var reset := _find_button_exact(self, label)
		if reset != null:
			reset.name = "ArchitectureReset"
			result.append(reset)
			break
	return result

func _publish_behavior_state() -> void:
	_set_dataset("novelforgeInteractionRevision", str(_interaction_revision))
	_set_dataset("novelforgePublicationProfile", str(_publication_profiles()[_publication_profile]["id"]))
	_set_dataset("novelforgePublicationArtifact", str(_publication_profiles()[_publication_profile]["artifact"]))
	_set_dataset("novelforgeHomeCapability", str(_home_capability_index))
	_set_dataset("novelforgeHomeBudget", str(_home_budget))
	var ready := true
	for value in _home_gates:
		if not bool(value):
			ready = false
	_set_dataset("novelforgeHomeReady", "true" if ready else "false")
	_set_dataset("novelforgeArchitectureNode", str(_architecture_selected))
	_set_dataset("novelforgeArchitectureRunStep", str(_architecture_run_step))
	_set_dataset("novelforgeAgentHost", str(AGENT_HOSTS[_agent_host_index]))
	_set_dataset("novelforgeGlyphAudit", "pass" if not _tree_contains_forbidden_decorative_text(self) else "fail")
	_publish_interaction_targets()

func _publish_control_targets(key: String, buttons: Array[Button]) -> void:
	var parts: Array[String] = []
	for button in buttons:
		if button == null or not is_instance_valid(button):
			continue
		var rect := button.get_global_rect()
		parts.append("%s,%.1f,%.1f,%.1f,%.1f" % [button.name, rect.position.x, rect.position.y, rect.size.x, rect.size.y])
	_set_dataset(key, ";".join(parts))

func _tree_contains_forbidden_decorative_text(node: Node) -> bool:
	if node is Label:
		if _has_forbidden_decorative_text((node as Label).text):
			return true
	elif node is Button:
		if _has_forbidden_decorative_text((node as Button).text):
			return true
	for child in node.get_children():
		if _tree_contains_forbidden_decorative_text(child):
			return true
	return false

func _has_forbidden_decorative_text(text: String) -> bool:
	for glyph in ["🎀", "🧵", "🫧", "🧠", "📖", "📚", "✨", "🌸", "🛠"]:
		if text.contains(glyph):
			return true
	return false

func _find_button_contains(node: Node, needle: String) -> Button:
	for child in node.get_children():
		if child is Button and (child as Button).text.contains(needle):
			return child as Button
		var nested := _find_button_contains(child, needle)
		if nested != null:
			return nested
	return null

func _find_button_prefix(node: Node, prefix: String) -> Button:
	for child in node.get_children():
		if child is Button and (child as Button).text.begins_with(prefix):
			return child as Button
		var nested := _find_button_prefix(child, prefix)
		if nested != null:
			return nested
	return null
