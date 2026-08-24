pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 复刻自 IAA 的 DslInstancePicker 控件层：选择器 + 加载指示器 + 刷新按钮
// 裸控件版本，不带 FormField / FormBinder 封装。需要 label/binding 请使用 FormInstancePicker。
// 对齐 IAA 的 DslInstancePicker：loading 时显示占位项、禁用交互、刷新按钮文案切换。
RowLayout {
    id: root

    property var options: []
    property bool loading: false
    property bool enabled: true
    property int currentIndex: -1
    readonly property var currentValue: comboBox.currentValue

    signal activated()
    signal refreshTriggered()

    Select {
        id: comboBox
        Layout.fillWidth: true
        enabled: root.enabled && !root.loading
        model: root.loading ? [{label: "载入中...", value: ""}] : (root.options || [])
        textRole: "label"
        valueRole: "value"
        currentIndex: root.loading ? 0 : root.currentIndex
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
        enabled: root.enabled && !root.loading
        onClicked: root.refreshTriggered()
    }
}
