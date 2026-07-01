import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../"
import "formUtils.js" as F

RowLayout {
    id: root
    Layout.fillWidth: true
    property string label: ""
    property string help: ""
    property string value: ""
    property string placeholder: ""
    property var binder: null
    property string field: ""

    signal userEdited(string v)

    readonly property var _eb: F.effectiveBinder(binder, parent)

    // 注意：必须显式引用 _eb.data，否则 QML 绑定引擎不会追踪 get() 内部读取的 data，
    // 导致 data 从 null 变为实际对象时 _val 不重新求值（表单字段全空）。
    readonly property string _val: {
        var _ = _eb ? _eb.data : null   // 强制建立对 _eb.data 的绑定依赖
        return (_eb && field) ? _eb.get(field, "") : value
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

    TextField {
        Layout.fillWidth: true
        text: root._val
        placeholderText: root.placeholder
        onTextEdited: {
            if (root._eb && root.field) root._eb.set(root.field, text)
            else root.userEdited(text)
        }
    }
}
