import QtQuick

// Shell slot 宿主：按 slotName 加载注册的 QML 组件序列。
// 作为 Repeater 派生组件，需置于 RowLayout / ColumnLayout / Item 内使用。
//
// 组件 URL 与控制器注入：
//   - source 由 ShellRegistry.slotItemsJson 提供的 url（file:// URL）加载；
//   - controllerRole 非空时，将解析到的控制器赋给 item 的 controller 属性
//     （下游组件按约定声明 `property var controller`）；
//   - fill 为 true 时每个组件锚定填满父项（用于整页 slot，如总览页）。
Repeater {
    id: root

    property string slotName: ""
    property var tab: null
    property bool fill: false

    model: root.slotName.length > 0
        ? JSON.parse(ShellRegistry.slotItemsJson(root.slotName))
        : []

    delegate: Loader {
        required property int index
        required property var modelData

        anchors.fill: root.fill ? parent : undefined
        source: modelData.url

        onLoaded: {
            if (!modelData.controllerRole)
                return
            var ctrl = root.tab
                ? root.tab.controller(modelData.controllerRole)
                : ShellRegistry.globalController(modelData.controllerRole)
            // 下游组件按约定声明 controller 属性；未声明时跳过，避免误加动态属性
            if (item && item.hasOwnProperty("controller"))
                item.controller = ctrl
        }
    }
}
