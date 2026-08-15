extends Node

var _window = null
var _document = null
var _popstate_callback = null

func _ready() -> void:
	if not OS.has_feature("web"):
		return

	_window = JavaScriptBridge.get_interface("window")
	_document = JavaScriptBridge.get_interface("document")
	if _window == null or _document == null:
		return

	# main.gd keeps a defensive reload fallback for hosts that do not install this
	# bridge. Claim the guard before the parent _ready() runs, then bind popstate
	# directly back into the live Godot scene so browser history does not reboot it.
	_window.__novelforgePopstateReloadInstalled = true
	_popstate_callback = JavaScriptBridge.create_callback(_on_popstate)
	_window.addEventListener("popstate", _popstate_callback)
	_document.documentElement.dataset.novelforgeHistory = "live"
	_publish_route(_browser_path())

func _exit_tree() -> void:
	if not OS.has_feature("web"):
		return
	if _window != null and _popstate_callback != null:
		_window.removeEventListener("popstate", _popstate_callback)

func _on_popstate(_args: Array) -> void:
	var path := _browser_path()
	var host := get_parent()
	if is_instance_valid(host) and host.has_method("_navigate"):
		host.call("_navigate", path, false)
		var locale_bridge = host.get_node_or_null("LocaleBridge")
		if locale_bridge != null and locale_bridge.has_method("apply_current_locale"):
			locale_bridge.call_deferred("apply_current_locale")
	_publish_route(path)

func _browser_path() -> String:
	if _window == null:
		return "/"
	return str(_window.location.pathname)

func _publish_route(path: String) -> void:
	if _document != null:
		_document.documentElement.dataset.novelforgeRoute = path
