import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../"
import "formUtils.js" as F

ColumnLayout {
    id: root
    Layout.fillWidth: true
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

    // 自动注册 label ↔ field 映射至 SettingsPage（仅当通过 binder+field 使用时）
    FieldRegistrar {
        id: _registrar
        startParent: root.parent
        binder: root._eb
        field: root.field
        label: root.label
        // binder.prefix 变化时触发重同步
        prefixRevision: root._eb ? (root._eb.prefix.length) : 0
    }
    // prefix 字符串变化需额外监听（length 不足以覆盖同长度不同值，补充 Connections）
    Connections {
        target: root._eb
        enabled: !!root._eb && !!root.field && !!root.label
        function onPrefixChanged() { _registrar.prefixRevision++ }
    }

    RowLayout {
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

    FormError {
        Layout.leftMargin: 4
        info: root._eb ? root._eb.error(root.field) : null
    }
}