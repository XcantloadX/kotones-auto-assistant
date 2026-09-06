import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EuiShell
import "../components/form"

// 控制页顶部通知区：旧版培育引擎废弃警告。
ColumnLayout {
    id: root

    required property var tab

    readonly property var settingsCtrl: tab ? tab.settingsCtrl : null
    readonly property bool produceEngineLegacy: (settingsCtrl?.config?.profile?.tasks?.produce?.produce_engine) === "legacy"

    FormNotice {
        Layout.fillWidth: true
        visible: root.produceEngineLegacy
        style: "warning"
        content: "旧版培育引擎已废弃，请尽快在 设置→培育→培育引擎 切换到新版培育引擎。"
    }
}
