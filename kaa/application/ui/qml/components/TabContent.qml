import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 单 tab 占位组件。
// 注意：WebEngineView 不能放在单独的 .qml 文件中作为 Repeater 的 delegate，
// 会导致 PySide6 段错误 (Qt bug: QQmlComponent 创建 WebEngineView 时崩溃)。
// WebEngineView 应在 main.qml 的 Repeater delegate 中内联创建。
Item {
    id: root

    required property int index

    readonly property string gradioUrl: TabManager.gradioUrlAt(index)

    Column {
        anchors.centerIn: parent
        spacing: 8

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Tab #" + root.index
            font.pixelSize: 18
            font.bold: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.gradioUrl
            font.pixelSize: 13
            opacity: 0.6
        }
    }
}
