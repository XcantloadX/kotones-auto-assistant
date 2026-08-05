import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../controls"
import "../"
import "formUtils.js" as F

RowLayout {
    id: root
    Layout.fillWidth: true
    property string label: ""
    property string help: ""
    property var options: []
    property var value: null
    property var binder: null
    property string field: ""

    signal userSelected(var v)

    readonly property var _eb: F.effectiveBinder(binder, parent)

    // 注意：必须显式引用 _eb.data，否则 QML 绑定引擎不会追踪 get() 内部读取的 data，
    // 导致 data 从 null 变为实际对象时 _val 不重新求值（表单字段全空）。
    readonly property var _val: {
        var _ = _eb ? _eb.data : null   // 强制建立对 _eb.data 的绑定依赖
        return (_eb && field)
            ? _eb.get(field, options.length > 0 ? options[0].value : null)
            : value
    }

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

    SegmentedButton {
        Layout.fillWidth: true
        model: root.options
        textRole: "label"
        valueRole: "value"
        value: root._val
        onActivated: function(index, v) {
            if (root._eb && root.field) root._eb.set(root.field, v)
            else root.userSelected(v)
        }
    }
}
