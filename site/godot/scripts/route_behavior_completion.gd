extends "res://scripts/post_merge_stabilization.gd"

# Final route behavior completion for controls that were still decorative in
# the post-merge Godot product. This layer only mirrors deterministic browser-
# local Solid interactions; it does not add Project/Core authority.

var _inspect_demo_loaded := false
var _inspect_notice := ""
var _inspect_buttons: Array[Button] = []

var _playground_mode := "DRAFT"
var _playground_source := ""
var _playground_ran := false
var _playground_buttons: Array[Button] = []
var _playground_editor: TextEdit
var _playground_run_button: Button
var _playground_clear_button: Button

const PLAYGROUND_MODES := ["DRAFT", "REVISE", "AUDIT", "PLAN-CHAPTER"]
const PLAYGROUND_PURPOSES_EN := {
	"DRAFT": "Preview the path from frozen context into scene simulation, character action, and event-first raw drafting.",
	"REVISE": "Route draft failures back to the owning layer and compare repair candidates instead of defaulting to sentence polish.",
	"AUDIT": "Show what an independent quality audit consumes and emits without granting authority.",
	"PLAN-CHAPTER": "Preview chapter planning with sparse context and long-horizon constraints while preserving causal alternatives.",
}
const PLAYGROUND_PURPOSES_ZH := {
	"DRAFT": "从冻结上下文进入场景模拟、人物行动与 event-first raw draft 之前的执行预览。",
	"REVISE": "把现稿问题路由回真正 owning layer，并比较 repair candidate，而不是默认句子润色。",
	"AUDIT": "展示独立质量审查读取什么、产生什么 evidence，以及为什么 semantic result 本身不授予 authority。",
	"PLAN-CHAPTER": "展示章节规划如何利用稀疏上下文与长期约束，同时保留因果分叉空间。",
}

func _build() -> void:
	_inspect_buttons.clear()
	_playground_buttons.clear()
	_playground_editor = null
	_playground_run_button = null
	_playground_clear_button = null
	super._build()
	_repair_architecture_wide_geometry()

# A rebuilt ScrollContainer cannot accept its old scroll value reliably until
# the new child minimum sizes have completed one deferred layout turn. The
# lower helper restores synchronously and can be clamped to zero; override it at
# the production entrypoint and use the same deferred restore path as viewport
# resize stabilization.
func _rebuild_at_scroll(scroll_y: int) -> void:
	_build()
	_publish_ready()
	call_deferred("_restore_scroll_position", scroll_y)

# The generic wide-page clamp preserves most routes, but Architecture has a
# mixed geometry contract: a fixed-width copy column plus a diagram and action
# controls whose source coordinates were derived from the pre-clamp page width.
# Rebuild the diagram from the final bounded hero width and restore the two
# action clusters from their container-relative formulas. This runs only above
# the Solid page max; 1440/compact/phone remain untouched.
func _repair_architecture_wide_geometry() -> void:
	if _current_route() != "/architecture" or _layout != "desktop" or _stage == null:
		return
	if _solid_viewport_width() <= SOLID_PAGE_MAX:
		return
	var hero: Panel = null
	var execution: Panel = null
	for child in _stage.get_children():
		if not child is Panel:
			continue
		var panel := child as Panel
		if absf(panel.size.x - SOLID_INNER_MAX) > 8.0:
			continue
		if absf(panel.position.y - 122.0) <= 8.0:
			hero = panel
		elif panel.position.y > 560.0 and panel.position.y < 760.0:
			execution = panel
	if hero != null:
		var old_grid: Control = null
		for child in hero.get_children():
			if child is Panel and child.get_child_count() >= 20:
				old_grid = child as Control
				break
		if old_grid != null:
			hero.remove_child(old_grid)
			old_grid.queue_free()
		_build_architecture_grid(
			hero,
			Vector2(hero.size.x * 0.59, 43.0),
			Vector2(hero.size.x * 0.38, maxf(hero.size.y - 86.0, 240.0)),
			false
		)
		var docs := _find_button_contains(hero, "architecture docs")
		if docs != null:
			docs.position = Vector2(44.0, 382.0 if _locale == "en-US" else 345.0)
			docs.size = Vector2(220.0, 44.0)
		var play := _find_button_exact(hero, "▷ Playground")
		if play != null:
			play.position = Vector2(280.0, 382.0 if _locale == "en-US" else 345.0)
			play.size = Vector2(150.0, 44.0)
	if execution != null:
		var simulate := _find_button_contains(execution, "Simulate")
		if simulate == null:
			simulate = _find_button_contains(execution, "模拟")
		if simulate != null:
			simulate.position = Vector2(execution.size.x - 260.0, 17.0)
			simulate.size = Vector2(155.0, 44.0)
		var reset := _find_button_exact(execution, "Reset")
		if reset == null:
			reset = _find_button_exact(execution, "重置")
		if reset != null:
			reset.position = Vector2(execution.size.x - 95.0, 17.0)
			reset.size = Vector2(75.0, 44.0)
	_set_dataset("novelforgeArchitectureWideHero", "bounded-two-column")

# -----------------------------------------------------------------------------
# Inspector: the existing demo/reset path is fully deterministic and mirrors
# Solid. Folder ingestion is not faked; the canvas explicitly reports that the
# browser-native directory bridge is not yet implemented in the Godot runtime.
# -----------------------------------------------------------------------------

func _build_project_picker(pos: Vector2, picker_size: Vector2, phone: bool) -> void:
	if _inspect_demo_loaded:
		_build_inspector_demo_summary(pos, picker_size, phone)
		return
	var picker := _panel(pos, picker_size, Color("fffdfc"), 25, Color("cbd7f1"), 1)
	_stage.add_child(picker)
	var tag := _panel(Vector2(24, 18), Vector2(112, 30), C.editorial_soft, 8, Color("efc8d9"), 1)
	var tag_text := _label("PROJECT FILES", 10, 760, C.editorial)
	tag_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tag_text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	tag_text.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	tag.add_child(tag_text)
	picker.add_child(tag)
	var icon_box := _panel(Vector2(picker_size.x / 2.0 - 30, 74), Vector2(60, 60), C.runtime_soft, 16, Color("cfc3ee"), 1, Color(0.18,0.12,0.24,0.05), 5)
	var house := _label("⌂", 28, 600, C.runtime)
	house.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	house.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	house.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	icon_box.add_child(house)
	picker.add_child(icon_box)
	var title := _label("Choose a NovelForge Project" if _locale == "en-US" else "选择 NovelForge Project", 30 if not phone else 25, 740, C.ink)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.position = Vector2(20, 150)
	title.size = Vector2(picker_size.x - 40, 46)
	picker.add_child(title)
	var body := _label("The inspector detects novelforge.toml, the framework lock, optional attestation, core\nlogical directories, and quality evidence surfaces." if _locale == "en-US" else "检查器会识别 novelforge.toml、Framework lock、可选 attestation、\n核心逻辑目录和质量证据面。", 14, 420, C.muted)
	body.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	body.position = Vector2(30, 210)
	body.size = Vector2(picker_size.x - 60, 70)
	body.add_theme_constant_override("line_spacing", 4)
	picker.add_child(body)
	var button_w := 208.0
	var choose := _text_button("Choose project folder" if _locale == "en-US" else "选择 Project 文件夹", Vector2(picker_size.x / 2.0 - button_w - 6, 294), Vector2(button_w, 46), Color("80b7ec"), Color.WHITE, 15, 600, 8)
	choose.name = "InspectorChooseFolder"
	choose.accessibility_name = "Choose project folder"
	choose.pressed.connect(_inspect_folder_unavailable)
	choose.focus_entered.connect(_record_focus.bind(choose.name))
	picker.add_child(choose)
	_inspect_buttons.append(choose)
	var demo := _mixed_text_button("✦ Load demo project" if _locale == "en-US" else "✦ 加载演示 Project", Vector2(picker_size.x / 2.0 + 6, 294), Vector2(205, 46), C.runtime_soft, C.runtime, 15, 600, 8)
	demo.name = "InspectorLoadDemo"
	demo.accessibility_name = "Load demo project"
	demo.pressed.connect(_inspect_load_demo)
	demo.focus_entered.connect(_record_focus.bind(demo.name))
	picker.add_child(demo)
	_inspect_buttons.append(demo)
	if phone:
		choose.position = Vector2(28, 308)
		choose.size.x = picker_size.x - 56
		demo.position = Vector2(28, 364)
		demo.size.x = picker_size.x - 56
	if _inspect_notice != "":
		var notice := _label(_inspect_notice, 12, 520, C.editorial)
		notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		notice.position = Vector2(28, picker_size.y - 46)
		notice.size = Vector2(picker_size.x - 56, 38)
		picker.add_child(notice)

func _build_inspector_demo_summary(pos: Vector2, picker_size: Vector2, phone: bool) -> void:
	var panel := _panel(pos, picker_size, Color("fffdfc"), 25, Color("b9dbce"), 1, Color(0.18,0.12,0.24,0.04), 4)
	_stage.add_child(panel)
	var eyebrow := _label("PROJECT SUMMARY" if _locale == "en-US" else "项目摘要", 10, 760, C.editorial)
	eyebrow.position = Vector2(28, 24)
	eyebrow.size = Vector2(180, 20)
	panel.add_child(eyebrow)
	var title := _label("Moonlit Archive", 28 if not phone else 24, 760, C.ink)
	title.position = Vector2(28, 50)
	title.size = Vector2(picker_size.x - 56, 42)
	panel.add_child(title)
	var status := _pill("✓ Structurally coherent" if _locale == "en-US" else "✓ 结构一致", Vector2(28, 100), Vector2(190, 30), C.valid_soft, Color("2f876d"), 11, 650, Color("b9dbce"))
	panel.add_child(status)
	var facts := [
		"84 files · 1.8 MB",
		"Project ID · MOONLIT-ARCHIVE",
		"Framework · 8.0-dev",
		"✓ novelforge.toml",
		"✓ novelforge.lock.json",
		"✓ framework.attestation.json",
	]
	if phone:
		facts = [
			"84 files · 1.8 MB",
			"ID · MOONLIT-ARCHIVE",
			"Framework · 8.0-dev",
			"✓ novelforge.toml",
			"✓ novelforge.lock.json",
			"✓ attestation",
		]
	var columns := 2
	var cell_w := (picker_size.x - 68) / 2.0
	for i in range(facts.size()):
		var row := _panel(Vector2(28 + (i % columns) * (cell_w + 12), 148 + (i / columns) * 48), Vector2(cell_w, 38), Color("fbf9fc"), 10, Color("e7deea"), 1)
		var text := _label(str(facts[i]), 10 if phone else 12, 580, C.ink)
		text.position = Vector2(10, 8)
		text.size = Vector2(cell_w - 20, 22)
		row.add_child(text)
		panel.add_child(row)
	var reset := _text_button("Inspect another project" if _locale == "en-US" else "检查另一个 Project", Vector2(28, picker_size.y - 58), Vector2(190, 42), C.runtime_soft, C.runtime, 13, 620, 8)
	reset.name = "InspectorReset"
	reset.accessibility_name = "Inspect another project"
	reset.pressed.connect(_inspect_reset)
	reset.focus_entered.connect(_record_focus.bind(reset.name))
	panel.add_child(reset)
	_inspect_buttons.append(reset)
	var disclaimer := _label("Browser-side structural inspection · authority=false" if _locale == "en-US" else "浏览器侧结构检查 · authority=false", 11, 520, C.muted)
	disclaimer.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	disclaimer.position = Vector2(230, picker_size.y - 52)
	disclaimer.size = Vector2(picker_size.x - 258, 28)
	panel.add_child(disclaimer)

func _inspect_load_demo() -> void:
	_inspect_demo_loaded = true
	_inspect_notice = ""
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

func _inspect_reset() -> void:
	_inspect_demo_loaded = false
	_inspect_notice = ""
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

func _inspect_folder_unavailable() -> void:
	_inspect_notice = "Folder import remains browser-native in Solid; Godot canvas import is not implemented." if _locale == "en-US" else "目录导入仍由 Solid 的浏览器原生实现负责；Godot canvas 尚未实现该导入。"
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

# -----------------------------------------------------------------------------
# Playground: actual task-mode selection, working text, run, and clear.
# -----------------------------------------------------------------------------

func _build_execution_board(pos: Vector2, board_size: Vector2, phone: bool) -> void:
	var board := _panel(pos, board_size, Color("fffdfc"), 25, Color("d9d0ec"), 1)
	_stage.add_child(board)
	var tag := _pill("✦ EXECUTION TRACE", Vector2(28, 24), Vector2(150, 30), Color("fffdfc"), C.runtime, 10, 720, Color("cfc3ee"))
	board.add_child(tag)
	var title := _label(_playground_mode, 18, 760, C.ink)
	title.position = Vector2(28, 65)
	title.size = Vector2(220, 30)
	board.add_child(title)
	var mode_y := 104.0
	for i in range(PLAYGROUND_MODES.size()):
		var mode := str(PLAYGROUND_MODES[i])
		var selected := mode == _playground_mode
		var width := 112.0 if mode == "PLAN-CHAPTER" else 82.0
		var button := _text_button(mode, Vector2(28 + (i % 2) * 124, mode_y + (i / 2) * 44), Vector2(width, 34), C.runtime_soft if selected else Color("fffdfc"), C.runtime if selected else C.muted, 10, 650, 8)
		button.name = "PlaygroundMode%s" % mode.replace("-", "")
		button.accessibility_name = "Select playground mode %s" % mode
		button.pressed.connect(_playground_select_mode.bind(mode))
		button.focus_entered.connect(_record_focus.bind(button.name))
		board.add_child(button)
		_playground_buttons.append(button)
	var purpose := _label(str((PLAYGROUND_PURPOSES_ZH if _locale == "zh-CN" else PLAYGROUND_PURPOSES_EN)[_playground_mode]), 11, 470, C.muted)
	purpose.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	purpose.position = Vector2(28, 198)
	purpose.size = Vector2(260, 74)
	purpose.add_theme_constant_override("line_spacing", 3)
	board.add_child(purpose)

	_playground_editor = TextEdit.new()
	_playground_editor.name = "PlaygroundSource"
	_playground_editor.text = _playground_source
	_playground_editor.placeholder_text = "Paste a scene, plan, draft, or review target…" if _locale == "en-US" else "粘贴场景、章节计划、现稿或审阅对象……"
	_playground_editor.position = Vector2(28, 278)
	_playground_editor.size = Vector2(260, 132 if not phone else 120)
	_playground_editor.custom_minimum_size = Vector2(44, 44)
	_playground_editor.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	_playground_editor.add_theme_font_override("font", _font(400))
	_playground_editor.add_theme_font_size_override("font_size", 12)
	_playground_editor.add_theme_color_override("font_color", C.ink)
	_playground_editor.add_theme_color_override("font_placeholder_color", C.muted)
	_playground_editor.add_theme_stylebox_override("normal", _button_box(Color("fbf9fc"), 10))
	_playground_editor.add_theme_stylebox_override("focus", _focus_box(10))
	_playground_editor.accessibility_name = "Playground working text"
	_playground_editor.text_changed.connect(_playground_source_changed.bind(_playground_editor))
	_playground_editor.focus_entered.connect(_record_focus.bind(_playground_editor.name))
	board.add_child(_playground_editor)

	_playground_run_button = _text_button("Generate demo trace" if _locale == "en-US" else "生成演示 trace", Vector2(28, 422), Vector2(160, 42), Color("80b7ec") if _playground_source.strip_edges() != "" else Color("e7e2ea"), Color.WHITE if _playground_source.strip_edges() != "" else C.muted, 12, 650, 8)
	_playground_run_button.name = "PlaygroundRun"
	_playground_run_button.accessibility_name = "Generate demo trace"
	_playground_run_button.pressed.connect(_playground_run)
	_playground_run_button.focus_entered.connect(_record_focus.bind(_playground_run_button.name))
	board.add_child(_playground_run_button)
	_playground_buttons.append(_playground_run_button)
	_playground_clear_button = _text_button("Clear" if _locale == "en-US" else "清空", Vector2(196, 422), Vector2(92, 42), C.runtime_soft, C.runtime, 12, 620, 8)
	_playground_clear_button.name = "PlaygroundClear"
	_playground_clear_button.accessibility_name = "Clear playground input"
	_playground_clear_button.pressed.connect(_playground_clear)
	_playground_clear_button.focus_entered.connect(_record_focus.bind(_playground_clear_button.name))
	board.add_child(_playground_clear_button)
	_playground_buttons.append(_playground_clear_button)
	_sync_playground_action_controls()

	var trace_pos := Vector2(320 if not phone else 28, 24 if not phone else 500)
	var trace_size := Vector2(board_size.x - (350 if not phone else 56), board_size.y - (48 if not phone else 530))
	var trace := _panel(trace_pos, trace_size, Color("fffdfc"), 18, Color("eee5f0"), 1)
	board.add_child(trace)
	var chars := _playground_source.strip_edges().length()
	var state := "prepared" if _playground_ran and chars >= 40 else ("needs_input" if _playground_ran else "deterministic mock")
	var trace_text := "Context → Evidence → Result\n\nMode · %s\nCharacters · %d\nStatus · %s\n\nNo model call · no Project write" % [_playground_mode, chars, state]
	var output := _label(trace_text, 14, 520, C.muted)
	output.position = Vector2(24, 28)
	output.size = Vector2(trace.size.x - 48, trace.size.y - 56)
	output.add_theme_constant_override("line_spacing", 8)
	trace.add_child(output)

func _playground_select_mode(mode: String) -> void:
	_playground_mode = mode
	_playground_ran = false
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

func _playground_source_changed(editor: TextEdit) -> void:
	_playground_source = editor.text
	_playground_ran = false
	_interaction_revision += 1
	_sync_playground_action_controls()
	_publish_behavior_state()

func _sync_playground_action_controls() -> void:
	var has_source := _playground_source.strip_edges() != ""
	if _playground_run_button != null and is_instance_valid(_playground_run_button):
		_playground_run_button.disabled = not has_source
		_playground_run_button.add_theme_color_override("font_color", Color.WHITE if has_source else C.muted)
		_playground_run_button.add_theme_color_override("font_disabled_color", C.muted)
		_playground_run_button.add_theme_stylebox_override("normal", _button_box(Color("80b7ec") if has_source else Color("e7e2ea"), 8))
		_playground_run_button.add_theme_stylebox_override("hover", _button_box(Color("6faee6") if has_source else Color("e7e2ea"), 8))
		_playground_run_button.add_theme_stylebox_override("pressed", _button_box(Color("5e9bd2") if has_source else Color("e7e2ea"), 8))
	if _playground_clear_button != null and is_instance_valid(_playground_clear_button):
		_playground_clear_button.disabled = not has_source

func _playground_run() -> void:
	if _playground_source.strip_edges() == "":
		return
	_playground_ran = true
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

func _playground_clear() -> void:
	_playground_source = ""
	_playground_ran = false
	_interaction_revision += 1
	_queue_rebuild_preserve_scroll()

# -----------------------------------------------------------------------------
# Non-authoritative QA evidence for real controls/state.
# -----------------------------------------------------------------------------

func _publish_behavior_state() -> void:
	super._publish_behavior_state()
	_set_dataset("novelforgeInspectorState", "demo" if _inspect_demo_loaded else ("notice" if _inspect_notice != "" else "empty"))
	_set_dataset("novelforgePlaygroundMode", _playground_mode)
	_set_dataset("novelforgePlaygroundChars", str(_playground_source.strip_edges().length()))
	_set_dataset("novelforgePlaygroundRan", "true" if _playground_ran else "false")
	_publish_route_behavior_targets()

func _publish_interaction_targets() -> void:
	super._publish_interaction_targets()
	_publish_route_behavior_targets()

func _publish_route_behavior_targets() -> void:
	_publish_control_targets("novelforgeInspectorTargets", _inspect_buttons)
	_publish_control_targets("novelforgePlaygroundTargets", _playground_buttons)
	if _playground_editor != null and is_instance_valid(_playground_editor):
		var rect := _playground_editor.get_global_rect()
		_set_dataset("novelforgePlaygroundEditor", "%.1f,%.1f,%.1f,%.1f" % [rect.position.x, rect.position.y, rect.size.x, rect.size.y])
	else:
		_set_dataset("novelforgePlaygroundEditor", "")
