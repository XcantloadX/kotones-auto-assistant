import QtQuick
import QtQuick.Layouts

// 表单字段容器，替代 GroupBox 内部的 ColumnLayout { width: parent.width; spacing: 8 }。
// 声明 binder 后，子字段无需重复写 binder: xxx，会自动向上爬树查找。
// 子字段仍可用显式 binder: override 覆盖，或用 value/onValueChanged 完全绕过。
ColumnLayout {
    property var binder: null
    // 子字段通过父链查找此 sentinel 属性来发现默认 binder
    readonly property var _formBinder: binder
    width: parent?.width ?? 0
    spacing: 8
}
