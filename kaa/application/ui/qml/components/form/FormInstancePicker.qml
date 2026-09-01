pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../controls"
import "../"
import "formUtils.js" as F

// Form 版本的 InstancePicker，复刻自 IAA 的 DslInstancePicker。
// 裸控件在 controls/InstancePicker.qml。
ColumnLayout {
    id: root
    Layout.fillWidth: true
    spacing: 4
    property string label: ""
    property string help: ""
    property var options: []
    property bool loading: false
    property var binder: null
    property string field: ""

    signal refreshTriggered()

    readonly property var _eb: F.effectiveBinder(binder, parent)
    readonly property var _val: {
        var _ = _eb ? _eb.data : null   // 强制建立对 _eb.data 的绑定依赖
        return (_eb && field) ? _eb.get(field, null) : null
    }

    FieldRegistrar {
        id: _registrar
        startParent: root.parent
        binder: root._eb
        field: root.field
        label: root.label
        prefixRevision: root._eb ? (root._eb.prefix.length) : 0
    }
    Connections {
        target: root._eb
        enabled: !!root._eb && !!root.field && !!root.label
        function onPrefixChanged() { _registrar.prefixRevision++ }
    }

    function indexOfValue(items, value) {
        if (!items) return -1
        for (var i = 0; i < items.length; ++i) {
            var item = items[i]
            if (item && item.value === value) return i
        }
        return -1
    }

    // 对齐 IAA DslInstancePicker.autoRefreshIfEmpty：可见且非 loading 时，若选项为空则自动触发刷新
    function autoRefreshIfEmpty() {
        if (root.loading) return
        var opts = root.options
        if (!opts || opts.length === 0) root.refreshTriggered()
    }

    Component.onCompleted: {
        if (visible) Qt.callLater(autoRefreshIfEmpty)
    }
    onVisibleChanged: {
        if (visible) Qt.callLater(autoRefreshIfEmpty)
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 0

        RowLayout {
            Layout.preferredWidth: 120
            spacing: 6

            Label { text: root.label; Layout.alignment: Qt.AlignVCenter }

            HelpTip {
                visible: root.help.length > 0
                richText: root.help
                Layout.alignment: Qt.AlignVCenter
            }
        }

        InstancePicker {
            Layout.fillWidth: true
            enabled: root.enabled
            options: root.options
            loading: root.loading
            currentIndex: root.indexOfValue(root.options, root._val)
            onActivated: {
                var v = currentValue
                if (root._eb && root.field) root._eb.set(root.field, v)
            }
            onRefreshTriggered: root.refreshTriggered()
        }
    }

    FormError {
        Layout.leftMargin: 126
        Layout.fillWidth: true
        info: root._eb ? root._eb.error(root.field) : null
    }
}
