import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../"
import "formUtils.js" as F

RowLayout {
    id: root
    property string label: ""
    property string help: ""
    property bool value: false
    property var binder: null
    property string field: ""
    property font font

    // 仅在用户点击时触发，不会因 value 绑定刷新而重复触发
    signal userToggled(bool checked)

    readonly property var _eb: F.effectiveBinder(binder, parent)

    // 注意：必须显式引用 _eb.data，否则 QML 绑定引擎不会追踪 get() 内部读取的 data，
    // 导致 data 从 null 变为实际对象时 _val 不重新求值（表单字段全空）。
    readonly property bool _val: {
        var _ = _eb ? _eb.data : null   // 强制建立对 _eb.data 的绑定依赖
        return (_eb && field) ? _eb.get(field, false) : value
    }

    CheckBox {
        text: root.label
        checked: root._val
        font: root.font
        onToggled: {
            if (root._eb && root.field) root._eb.set(root.field, checked)
            else root.userToggled(checked)
        }
    }

    HelpTip {
        visible: root.help.length > 0
        richText: root.help
        Layout.alignment: Qt.AlignVCenter
    }
}
