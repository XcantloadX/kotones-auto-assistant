import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../"
import "formUtils.js" as F

// 数字输入框。使用 TextField + IntValidator 限制只能输入数字。
ColumnLayout {
    id: root
    Layout.fillWidth: true
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

    RowLayout {
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

            // 输入有效时立即更新草稿，避免通过导航或快捷键保存时
            // 因输入框尚未失焦而漏掉编辑内容。
            onTextEdited: {
                if (acceptableInput) writeValue(parseInt(text, 10))
            }
            onActiveFocusChanged: { if (!activeFocus) commit() }

            function writeValue(v) {
                var out = root.write(v)
                if (root._eb && root.field) {
                    if (root._eb.get(root.field, null) !== out) root._eb.set(root.field, out)
                } else if (root.value !== out) {
                    root.value = out
                    root.valueModified(out)
                }
            }

            function commit() {
                var v = parseInt(text, 10)
                if (isNaN(v)) v = root.from
                v = Math.max(root.from, Math.min(root.to, v))
                writeValue(v)
                // 归一化后恢复数据绑定，确保切换方案等数据源变化
                // 能同步刷新输入框。
                text = Qt.binding(function() { return root.read(root._val).toString() })
            }
        }
    }

    FormError {
        Layout.leftMargin: root.labelWidth + 6
        info: root._eb ? root._eb.error(root.field) : null
    }
}