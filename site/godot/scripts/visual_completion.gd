extends "res://scripts/visual_completion_core.gd"

# Screenshot-driven finishing layer. The core completion layer owns product
# semantics and full route surfaces; this layer only corrects browser-visible
# typography/geometry defects that were proven by the full-surface QA captures.

func _build() -> void:
	super._build()
	_polish_decorative_copy()
	match _current_route():
		"/":
			_polish_home_surface()
		"/architecture":
			_polish_architecture_surface()
		"/publication":
			_polish_publication_surface()
	_set_dataset("novelforgeVisualPolish", "ready")

func _polish_decorative_copy() -> void:
	# Mixed-script kaomoji crossed Arabic/Thai/Symbol fallback boundaries in the
	# Web renderer and appeared as corrupted glyphs. Keep the Atelier warmth, but
	# use the deterministic symbol/CJK/Latin fallback set only.
	var cat := _find_label_exact(self, "ฅ^•ﻌ•^ฅ")
	if cat != null:
		cat.text = "♡ Loom"
		cat.add_theme_font_override("font", _mixed_font(550))
	var hint_en := _find_label_prefix(self, "Let’s weave something lovely today")
	if hint_en != null:
		hint_en.text = "Let’s weave something lovely today ♡"
		_hint_fit(hint_en)
	var hint_zh := _find_label_prefix(self, "今天也把故事织得更漂亮一点吧")
	if hint_zh != null:
		hint_zh.text = "今天也把故事织得更漂亮一点吧 ♡"
		_hint_fit(hint_zh)

func _hint_fit(label: Label) -> void:
	label.add_theme_font_override("font", _mixed_font(480))
	label.add_theme_font_size_override("font_size", 11 if _layout == "phone" else 12)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

func _polish_home_surface() -> void:
	if _layout != "phone":
		return
	var title_en := _find_label_prefix(self, "Real documentation now lives inside the product")
	if title_en != null:
		title_en.text = "Real documentation\nlives inside the product"
		_title_mobile_fit(title_en, 22, 76)
	var title_zh := _find_label_prefix(self, "真实文档已经进入产品本身")
	if title_zh != null:
		title_zh.text = "真实文档已经\n进入产品本身"
		_title_mobile_fit(title_zh, 22, 76)
	var body_en := _find_label_prefix(self, "Docs are compiled at build time from repository authority")
	if body_en != null:
		body_en.text = "Docs are compiled from repository authority\ninto the product for search and deep links."
		_body_mobile_fit(body_en, 11, 58)
	var body_zh := _find_label_prefix(self, "文档在构建时从仓库权威源编译进站点")
	if body_zh != null:
		body_zh.text = "文档从仓库权威源编译进产品，\n可直接搜索、阅读与深链。"
		_body_mobile_fit(body_zh, 11, 58)
	_shorten_home_doc_row("See how Project, Context, Gate, and Settlement divide ownership.", "Project → Context → Gate → Settlement.")
	_shorten_home_doc_row("How accepted text enters deterministic publication derivation.", "Accepted text → deterministic derivatives.")
	_shorten_home_doc_row("看 Project、Context、Gate 与 Settlement 如何分工。", "Project → Context → Gate → Settlement。")
	_shorten_home_doc_row("接受稿如何进入确定性的出版派生链。", "接受稿 → 确定性出版派生。")

func _shorten_home_doc_row(source: String, replacement: String) -> void:
	var label := _find_label_exact(self, source)
	if label != null:
		label.text = replacement
		label.add_theme_font_size_override("font_size", 9)

func _polish_architecture_surface() -> void:
	if _locale == "zh-CN":
		_polish_architecture_cjk_hero()
	if _layout == "phone":
		_polish_architecture_mobile_detail()

func _polish_architecture_cjk_hero() -> void:
	var title := _find_label_prefix(self, "看一次 NovelForge")
	if title == null:
		return
	title.text = "看一次 NovelForge\n如何穿过整个系统。"
	title.add_theme_font_override("font", _cjk_font(720))
	if _layout == "desktop":
		title.position.y = 104.0
		title.size = Vector2(650.0, 132.0)
		title.add_theme_font_size_override("font_size", 48)
		title.add_theme_constant_override("line_spacing", -5)
		var lede := _find_label_prefix(self, "Project → Manager")
		if lede != null:
			lede.position.y = 250.0
			lede.size = Vector2(650.0, 62.0)
		var docs := _find_button_exact(self, "📚 阅读架构文档")
		if docs == null:
			docs = _find_button_exact(self, "阅读架构文档")
		if docs != null:
			docs.position.y = 326.0
		var play := _find_button_exact(self, "▷ Playground")
		if play != null:
			play.position.y = 329.0
	elif _layout == "phone":
		title.position.y = 84.0
		title.size = Vector2(max(size.x - 68.0, 250.0), 120.0)
		title.add_theme_font_size_override("font_size", 36)
		title.add_theme_constant_override("line_spacing", -5)
		var lede_phone := _find_label_prefix(self, "Project → Manager")
		if lede_phone != null:
			lede_phone.position.y = 220.0
			lede_phone.size.y = 96.0
		var docs_phone := _find_button_exact(self, "📚 阅读架构文档")
		if docs_phone == null:
			docs_phone = _find_button_exact(self, "阅读架构文档")
		if docs_phone != null:
			docs_phone.position.y = 326.0
		var play_phone := _find_button_exact(self, "▷ Playground")
		if play_phone != null:
			play_phone.position.y = 378.0

func _polish_architecture_mobile_detail() -> void:
	var authority := _find_label_exact(self, "A single model output cannot overwrite Project authority.")
	if authority != null:
		authority.text = "Model output cannot\noverwrite Project\nauthority."
		authority.add_theme_font_size_override("font_size", 9)
		authority.size.y = 72.0
	var authority_zh := _find_label_exact(self, "Project 不能被一次模型输出覆盖。")
	if authority_zh != null:
		authority_zh.text = "模型输出不能覆盖\nProject authority。"
		authority_zh.add_theme_font_size_override("font_size", 9)
		authority_zh.size.y = 72.0

func _polish_publication_surface() -> void:
	if _layout != "phone":
		return
	var title_en := _find_label_prefix(self, "Every derivative resolves back to the same accepted manuscript")
	if title_en != null:
		title_en.text = "Every derivative resolves back\nto the same accepted manuscript."
		_title_mobile_fit(title_en, 15, 52)
	var title_zh := _find_label_prefix(self, "每个派生物都能回到同一份接受正文")
	if title_zh != null:
		title_zh.text = "每个派生物都能回到\n同一份接受正文。"
		_title_mobile_fit(title_zh, 15, 52)

func _title_mobile_fit(label: Label, font_size: int, height: float) -> void:
	label.add_theme_font_size_override("font_size", font_size)
	label.size.y = height
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_constant_override("line_spacing", 1)

func _body_mobile_fit(label: Label, font_size: int, height: float) -> void:
	label.add_theme_font_size_override("font_size", font_size)
	label.size.y = height
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_constant_override("line_spacing", 3)
