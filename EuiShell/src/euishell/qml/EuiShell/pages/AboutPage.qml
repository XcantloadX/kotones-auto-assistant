import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import ".."

// 关于页：应用信息 + 外链 + 下游附加内容。
// 页面统一契约：tab / navigation / fullscreenMode。
PageContainer {
    id: root
    title: "关于"

    required property var tab
    property var navigation: null
    property string fullscreenMode: ""

    // 下游扩展点（由 EuiShellApp 透传）
    property list<EuiLink> aboutLinks: []
    property Component aboutExtra: null

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16
        width: Math.max(160, implicitWidth)

        Image {
            source: "file:///" + splash.iconPath
            width: 160
            height: 160
            Layout.preferredWidth: 160
            Layout.preferredHeight: 160
            Layout.minimumWidth: 160
            Layout.maximumWidth: 160
            Layout.minimumHeight: 160
            Layout.maximumHeight: 160
            Layout.alignment: Qt.AlignHCenter
            fillMode: Image.PreserveAspectFit
        }

        Label {
            text: splash.appName
            font.pixelSize: 28
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: "版本 " + (splash ? splash.appVersion : "dev")
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: false

            Repeater {
                model: root.aboutLinks
                delegate: Link {
                    required property var modelData
                    label: modelData.label
                    href: modelData.url
                }
            }
        }

        // ── 下游附加内容 slot ─────────────────────────
        Loader {
            sourceComponent: root.aboutExtra
            Layout.alignment: Qt.AlignHCenter
            onLoaded: if (item && item.hasOwnProperty("tab")) item.tab = root.tab
        }
    }
}
