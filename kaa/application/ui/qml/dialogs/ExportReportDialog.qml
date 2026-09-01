import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: root

    property var feedbackCtrl: null
    property bool submitting: false
    signal exportSucceeded(string message)
    property string sanitizedTitle: {
        var value = titleField.text.trim()
        value = value.replace(/[\\/:*?"<>|]/g, "_")
        return value.substring(0, 30) || "无标题"
    }
    property string errorMessage: ""

    title: "导出报告"
    modal: true
    closePolicy: submitting ? Popup.NoAutoClose : Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: Overlay.overlay
    width: Math.min(600, parent ? parent.width - 80 : 600)
    standardButtons: Dialog.NoButton

    FileDialog {
        id: saveFileDialog
        title: "保存报告"
        fileMode: FileDialog.SaveFile
        nameFilters: ["ZIP 文件 (*.zip)", "所有文件 (*)"]
        currentFile: "bug_" + Qt.formatDateTime(new Date(), "yy-MM-dd-HH-mm-ss") + "_" + root.sanitizedTitle + ".zip"
        onAccepted: {
            var path = selectedFile.toString()
            if (path.startsWith("file:///")) {
                path = decodeURIComponent(path.substring(8))
            }
            if (path.length === 0) {
                return
            }
            if (!path.toLowerCase().endsWith(".zip")) {
                path += ".zip"
            }
            root.submitting = true
            root.errorMessage = ""
            root.feedbackCtrl.submitReport(titleField.text, descField.text, path)
        }
    }

    Connections {
        target: root.feedbackCtrl
        function onReportDone(msg) {
            root.submitting = false
            root.close()
            root.exportSucceeded(msg)
        }
        function onReportFailed(msg) {
            root.submitting = false
            root.errorMessage = msg
        }
    }

    onOpened: {
        errorMessage = ""
        submitting = false
        titleField.forceActiveFocus()
    }

    ColumnLayout {
        width: parent.width
        spacing: 10

        Label {
            text: "导出脚本运行报告，并将报告保存到本地后发送给开发者。"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: "标题"; Layout.preferredWidth: 60 }
            TextField {
                id: titleField
                Layout.fillWidth: true
                placeholderText: "简要描述问题"
                enabled: !root.submitting
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: "描述"; Layout.preferredWidth: 60 }
            TextArea {
                id: descField
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                placeholderText: "详细描述问题发生的过程、预期结果和实际结果"
                wrapMode: TextArea.Wrap
                enabled: !root.submitting
            }
        }

        Label {
            text: root.errorMessage
            color: "#d32f2f"
            visible: text.length > 0
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }

    footer: Rectangle {
        implicitHeight: 65
        color: root.palette.window

        Rectangle {
            width: parent.width
            height: 1
            color: root.palette.windowText
            opacity: 0.12
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 24
            spacing: 8

            Button {
                text: "取消"
                enabled: !root.submitting
                onClicked: root.close()
            }

            Button {
                text: "导出报告"
                highlighted: true
                enabled: !root.submitting && titleField.text.length > 0 && root.feedbackCtrl !== null
                onClicked: saveFileDialog.open()
            }
        }
    }
}
