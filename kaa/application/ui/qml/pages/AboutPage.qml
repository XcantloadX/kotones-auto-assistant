import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    title: "关于"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16
        width: Math.max(160, implicitWidth)

        Image {
            source: "../../icon.png"
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
            text: "琴音小助手 kaa"
            font.pixelSize: 28
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: "版本 " + (splash ? splash.appVersion : "dev")
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: "游戏数据 " + (GameDataCtrl.currentVersion || "未安装")
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: false
            Link { label: "GitHub"; href: "https://github.com/XcantloadX/kotones-auto-assistant" }
            Link { label: "Bilibili"; href: "https://space.bilibili.com/3546853903698457" }
            Link { label: "教程文档"; href: "https://www.kdocs.cn/l/cetCY8mGKHLj" }
            Link { label: "QQ 群"; href: "https://qm.qq.com/q/OI0C3rMmAs" }
        }
    }
}
