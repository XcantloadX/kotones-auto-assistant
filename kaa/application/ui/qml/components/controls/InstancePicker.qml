pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 复刻自 IAA 的 DslInstancePicker 控件层：选择器 + 加载指示器 + 刷新按钮
// 裸控件版本，不带 FormField / FormBinder 封装。需要 label/binding 请使用 FormInstancePicker。
RowLayout {
    id: root

    property var options: []
    property bool loading: false
    property int currentIndex: -1
    readonly property var currentValue: comboBox.currentValue

    signal activated()
    signal refreshTriggered()

    Select {
        id: comboBox
        Layout.fillWidth: true
        enabled: !root.loading
        model: root.options
        textRole: "label"
        valueRole: "value"
        currentIndex: root.currentIndex
        onActivated: root.activated()
    }

    BusyIndicator {
        visible: root.loading
        running: root.loading
        Layout.preferredWidth: 20
        Layout.preferredHeight: 20
    }

    Button {
        text: root.loading ? "获取中..." : "刷新"
        enabled: !root.loading
        onClicked: root.refreshTriggered()
    }
}
