import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EuiShell

// 控制页运行控制行内附加控件：完成后操作（关机/休眠）选择。
// 使用 KAA control 控制器（即时写入 tasks.end_game.*）。
RowLayout {
    id: root

    required property var tab

    readonly property var controlCtrl: tab ? tab.controller("control") : null

    Select {
        id: endActionCombo
        Layout.minimumWidth: 190
        textRole: "label"
        valueRole: "value"
        model: [
            { label: "完成后什么都不做", value: "nothing" },
            { label: "完成后关机", value: "shutdown" },
            { label: "完成后休眠", value: "hibernate" }
        ]
        onCurrentValueChanged: {
            if (currentValue && root.controlCtrl) root.controlCtrl.setEndAction(currentValue)
        }
        Component.onCompleted: currentValue = root.controlCtrl ? root.controlCtrl.endAction : "nothing"
        Connections {
            target: root.controlCtrl
            function onEndActionChanged() {
                endActionCombo.currentValue = root.controlCtrl.endAction
            }
        }
    }
}
