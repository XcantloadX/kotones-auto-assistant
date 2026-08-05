import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../"
import "formUtils.js" as F

// 数字输入框。使用 TextField + IntValidator 限制只能输入数字。
RowLayout {
    id: root
    property string label: ""
    property string help: ""
    property int from: 0
    property int to: 100
    property var value: 0
    property var read:  function(v) { return v ?? 0 }
    property var write: function(v) { return v }
    property int labelWidth: 120
    property var binder: null
    property string field: ""

    signal valueModified(var v)

    readonly property var _eb: F.effectiveBinder(binder, parent)

    // 注意：必须显式引用 _eb.data，否则 QML 绑定引擎不会追踪 get() 内部读取的 data，
    // 导致 data 从 null 变为实际对象时 _val 不重新求值（表单字段全空）。
    readonly property var _val: {
        var _ = _eb ? _eb.data : null   // 强制建立对 _eb.data 的绑定依赖
        return (_eb && field) ? _eb.get(field, from) : value
    }

    RowLayout {
        Layout.preferredWidth: root.labelWidth
        spacing: 6

        Label {
            text: root.label
            enabled: root.enabled
            Layout.alignment: Qt.AlignVCenter
        }

        HelpTip {
            visible: root.help.length > 0
            richText: root.help
            Layout.alignment: Qt.AlignVCenter
        }
    }

    TextField {
        id: inputField
        Layout.fillWidth: true
        text: root.read(root._val).toString()
        enabled: root.enabled
        validator: IntValidator { bottom: root.from; top: root.to }

        onActiveFocusChanged: { if (!activeFocus) commit() }

        function commit() {
            var v = parseInt(text, 10)
            if (isNaN(v)) v = root.from
            v = Math.max(root.from, Math.min(root.to, v))
            text = v.toString()
            var out = root.write(v)
            if (root._eb && root.field) root._eb.set(root.field, out)
            else { root.value = out; root.valueModified(out) }
        }
    }
}
