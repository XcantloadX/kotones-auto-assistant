import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 多选下拉框：Button + Popup + CheckBox 列表
Control {
    id: root

    property string label: ""
    property var model: []          // [{text: "...", value: ...}]
    property var selectedValues: [] // 内部用 set 快速查找
    signal selectionChanged()

    function _isSelected(v) { return selectedValues.indexOf(v) >= 0 }

    function _toggle(v) {
        var idx = selectedValues.indexOf(v)
        if (idx >= 0) {
            selectedValues.splice(idx, 1)
        } else {
            selectedValues.push(v)
        }
        selectedValues = selectedValues  // force binding re-eval
        root.selectionChanged()
    }

    function _displayText() {
        if (!selectedValues || selectedValues.length === 0) return "(未选择)"
        var texts = []
        for (var i = 0; i < model.length; i++) {
            if (_isSelected(model[i].value))
                texts.push(model[i].text)
        }
        return texts.join(", ")
    }

    implicitHeight: btn.implicitHeight
    implicitWidth: btn.implicitWidth

    Button {
        id: btn
        anchors.fill: parent
        text: root.label + ": " + root._displayText()
        onClicked: popup.open()

        Popup {
            id: popup
            y: btn.height + 2
            width: Math.max(300, btn.width)
            modal: true
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

            ColumnLayout {
                width: parent.width
                spacing: 4
                Repeater {
                    model: root.model
                    delegate: CheckBox {
                        width: parent.width
                        text: modelData.text
                        checked: root._isSelected(modelData.value)
                        onToggled: root._toggle(modelData.value)
                    }
                }
            }
        }
    }
}
