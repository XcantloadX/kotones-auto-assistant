import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 多选 Modal：Button 触发 Dialog，CheckBox 列表，OK / Cancel 确认
Control {
    id: root

    property string label: ""
    property var model: []          // [{text: "...", value: ...}]
    property var selectedValues: []
    signal selectionChanged()

    // 临时工作副本，用于 OK / Cancel 隔离
    property var _workingValues: []

    function _isSelected(v, arr) {
        return (arr || selectedValues).indexOf(v) >= 0
    }

    function _openDialog() {
        _workingValues = selectedValues.slice()
        dialog.open()
    }

    function _toggleWorking(v) {
        var idx = _workingValues.indexOf(v)
        if (idx >= 0) {
            _workingValues.splice(idx, 1)
        } else {
            _workingValues.push(v)
        }
        _workingValues = _workingValues  // force binding re-eval
    }

    function _selectAll() {
        var values = []
        for (var i = 0; i < model.length; i++)
            values.push(model[i].value)
        _workingValues = values
    }

    function _deselectAll() {
        _workingValues = []
    }

    function _invertSelection() {
        var values = []
        for (var i = 0; i < model.length; i++) {
            var v = model[i].value
            if (_workingValues.indexOf(v) < 0)
                values.push(v)
        }
        _workingValues = values
    }

    function _apply() {
        selectedValues = _workingValues
        root.selectionChanged()
    }

    function _cancel() {
        _workingValues = []
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
        onClicked: root._openDialog()

        Dialog {
            id: dialog
            title: root.label
            modal: true
            anchors.centerIn: Overlay.overlay

            width: Math.min(420, Overlay.overlay ? Overlay.overlay.width * 0.85 : 420)
            height: Math.min(480, Overlay.overlay ? Overlay.overlay.height * 0.7 : 480)

            padding: 16
            closePolicy: Popup.CloseOnEscape

            contentItem: ColumnLayout {
                spacing: 8
                RowLayout {
                    spacing: 6
                    Button { text: "全选"; onClicked: root._selectAll() }
                    Button { text: "全不选"; onClicked: root._deselectAll() }
                    Button { text: "反选"; onClicked: root._invertSelection() }
                    Item { Layout.fillWidth: true } // 撑满
                }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: root.model
                            delegate: CheckBox {
                                Layout.fillWidth: true
                                text: modelData.text
                                checked: root._isSelected(modelData.value, root._workingValues)
                                onToggled: root._toggleWorking(modelData.value)
                            }
                        }
                    }
                }
            }

            footer: DialogButtonBox {
                standardButtons: DialogButtonBox.Ok | DialogButtonBox.Cancel
                onAccepted: {
                    root._apply()
                    dialog.close()
                }
                onRejected: {
                    root._cancel()
                    dialog.close()
                }
            }
        }
    }
}
