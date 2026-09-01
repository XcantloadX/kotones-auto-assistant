import QtQuick

// 将 binder.prefix + field 映射为用户可见 label，注册到祖先 SettingsPage。
// 用法（在 Form* 内）：
//   FieldRegistrar { id: _reg; startParent: root.parent; binder: root._eb; field: root.field; label: root.label }
QtObject {
    id: root
    property var startParent: null
    property var binder: null
    property string field: ""
    property string label: ""

    property var _host: null
    property string _prevPath: ""

    function _fullPath() {
        if (!field) return ""
        var prefix = (binder && binder.prefix) ? binder.prefix : ""
        return prefix ? (prefix + "." + field) : field
    }

    function _findHost(p) {
        while (p) {
            if (p && p.registerField !== undefined && p.unregisterField !== undefined)
                return p
            // QML parent 链：优先 parent，其次 fallback 到 parent 的 parent（处理 QtObject 寄宿）
            var np = p.parent
            // 若无 visual parent，尝试通过对象树的 parent（部分 Component 场景）
            if (!np && p.parent === undefined && p["parent"] !== undefined) np = p["parent"]
            p = np
        }
        return null
    }

    function _sync() {
        if (!_host) _host = _findHost(startParent)
        if (!_host || !field || !label) return
        var cur = _fullPath()
        if (!cur) return
        if (_prevPath && _prevPath !== cur) {
            _host.unregisterField(_prevPath)
        }
        _host.registerField(cur, label)
        _prevPath = cur
    }

    function _detach() {
        if (_host && _prevPath) {
            _host.unregisterField(_prevPath)
            _prevPath = ""
        }
    }

    Component.onCompleted: _sync()
    Component.onDestruction: _detach()

    onLabelChanged: _sync()
    onFieldChanged: _sync()
    onBinderChanged: _sync()
    onStartParentChanged: { _host = _findHost(startParent); _sync() }

    // binder.prefix 变化需外部通过 prefixRevision 触发；见各 Form* 的 Connections
    property int prefixRevision: 0
    onPrefixRevisionChanged: _sync()
}
