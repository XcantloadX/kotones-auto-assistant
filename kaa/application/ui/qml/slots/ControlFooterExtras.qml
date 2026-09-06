import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EuiShell
import "../dialogs"

// 控制页底部附加区：报告反馈引导 + 调试模式警告。
ColumnLayout {
    id: root

    required property var tab

    readonly property var settingsCtrl: tab ? tab.settingsCtrl : null
    readonly property bool keepScreenshots: (settingsCtrl?.config?.profile?.keep_screenshots) ?? false
    readonly property var feedbackCtrl: tab ? tab.controller("feedback") : null

    // ── 引导提示 ──────────────────────────────
    RowLayout {
        Layout.fillWidth: true

        Label {
            text: "脚本报错或者卡住？点击"
            color: palette.placeholderText
        }

        Button {
            text: "导出报告"
            padding: 0
            leftPadding: 8
            rightPadding: 8
            onClicked: feedbackDialog.open()
        }

        Label {
            text: "并发送给开发者反馈！"
            color: palette.placeholderText
        }
    }

    // ── 调试模式警告 ──────────────────────────
    FormNotice {
        Layout.fillWidth: true
        visible: root.keepScreenshots
        style: "warning"
        title: "调试模式"
        content: "当前启用了调试功能「保留截图数据」，调试结束后正常使用时建议关闭此选项！"
    }

    ExportReportDialog {
        id: feedbackDialog
        feedbackCtrl: root.feedbackCtrl
        onExportSucceeded: function(message) {
            resultDialog.message = message
            Qt.callLater(function() { resultDialog.open() })
        }
    }

    ReportExportResultDialog {
        id: resultDialog
    }
}
