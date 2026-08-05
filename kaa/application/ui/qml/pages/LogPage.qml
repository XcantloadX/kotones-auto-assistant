import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

PageContainer {
    id: root
    title: "日志"
    property var logBridge
    Component.onCompleted: {
        if (root.logBridge) {
            var entries = root.logBridge.bufferedEntries()
            for (var i = 0; i < entries.length; i++) {
                var e = entries[i]
                root.appendText(e.text || "", e.stream || "normal")
            }
        }
    }
    property int maxLines: 2000
    property string pendingText: ""
    property var pendingLines: []
    property bool wrapEnabled: true

    readonly property bool darkTheme: Qt.styleHints.colorScheme === Qt.ColorScheme.Dark

    headerActions: RowLayout {
        spacing: 10
        CheckBox {
            text: "自动换行"
            checked: root.wrapEnabled
            onToggled: root.wrapEnabled = checked
        }
        Button {
            text: "清除"
            onClicked: {
                logModel.clear()
                root.pendingText = ""
                root.pendingLines = []
                batchTimer.stop()
                logView.maxLineWidth = 0
            }
        }
        Label { text: "最多 " + root.maxLines + " 行" }
    }

    ListModel {
        id: logModel
    }

    Timer {
        id: batchTimer
        interval: 50
        repeat: false
        onTriggered: root.flushPending()
    }

    function resolveColor(line, streamName) {
        var colors = {
            normal:   root.darkTheme ? "#e5e7eb" : "#111827",
            debug:    root.darkTheme ? "#94a3b8" : "#64748b",
            warning:  root.darkTheme ? "#f59e0b" : "#b45309",
            error:    root.darkTheme ? "#f87171" : "#b91c1c",
            critical: root.darkTheme ? "#ef4444" : "#7f1d1d",
            stderr:   root.darkTheme ? "#f87171" : "#b91c1c",
        }
        if (streamName === "stderr") return colors.stderr
        if (line.indexOf("[CRITICAL]") >= 0 || line.indexOf("CRITICAL") >= 0) return colors.critical
        if (line.indexOf("[ERROR]")    >= 0 || line.indexOf("ERROR")    >= 0) return colors.error
        if (line.indexOf("[WARNING]")  >= 0 || line.indexOf("WARNING")  >= 0 || line.indexOf("WARN") >= 0) return colors.warning
        if (line.indexOf("[DEBUG]")    >= 0 || line.indexOf("DEBUG")    >= 0) return colors.debug
        return colors.normal
    }

    function flushPending() {
        if (root.pendingLines.length === 0) return
        var lines = root.pendingLines
        root.pendingLines = []

        var overflow = logModel.count + lines.length - root.maxLines
        if (overflow > 0) {
            var fromModel = Math.min(overflow, logModel.count)
            var fromLines = overflow - fromModel
            if (fromModel > 0) logModel.remove(0, fromModel)
            if (fromLines > 0) lines = lines.slice(fromLines)
        }

        for (var i = 0; i < lines.length; i++) {
            logModel.append(lines[i])
        }
        logView.positionViewAtEnd()
    }

    function appendText(text, streamName) {
        if (!text) return
        var combined = root.pendingText + text
        var parts = combined.split(/\r?\n/)
        root.pendingText = parts.pop()
        for (var i = 0; i < parts.length; i++) {
            root.pendingLines.push({ logText: parts[i], stream: streamName })
        }
        if (!batchTimer.running) {
            batchTimer.restart()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        GroupBox {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "输出"

            Rectangle {
                anchors.fill: parent
                color: root.palette.base
                radius: 6
                clip: true

                ListView {
                    id: logView
                    anchors.fill: parent
                    anchors.margins: 8
                    model: logModel
                    clip: true
                    flickableDirection: Flickable.AutoFlickIfNeeded

                    property real maxLineWidth: 0
                    contentWidth: root.wrapEnabled ? width : Math.max(width, maxLineWidth)

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }
                    ScrollBar.horizontal: ScrollBar {
                        policy: root.wrapEnabled ? ScrollBar.AlwaysOff : ScrollBar.AsNeeded
                    }

                    WheelHandler {
                        acceptedModifiers: Qt.ShiftModifier
                        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                        target: null
                        blocking: true
                        onWheel: function(event) {
                            if (root.wrapEnabled) return
                            var delta = event.pixelDelta.y !== 0
                                ? event.pixelDelta.y
                                : event.angleDelta.y / 120 * 48
                            var bar = logView.ScrollBar.horizontal
                            var maxPos = Math.max(0, 1.0 - bar.size)
                            bar.position = Math.max(0, Math.min(maxPos, bar.position - delta / logView.contentWidth))
                            event.accepted = true
                        }
                    }

                    delegate: Text {
                        required property string logText
                        required property string stream

                        width: root.wrapEnabled ? logView.width : implicitWidth
                        text: logText
                        color: root.resolveColor(logText, stream)
                        font.family: Qt.platform.os === "windows"
                            ? "Consolas"
                            : Qt.platform.os === "osx"
                                ? "Menlo"
                                : "DejaVu Sans Mono"
                        font.pixelSize: 13
                        wrapMode: root.wrapEnabled ? Text.Wrap : Text.NoWrap
                        topPadding: 1
                        bottomPadding: 1
                        leftPadding: 2

                        Component.onCompleted: {
                            if (!root.wrapEnabled && implicitWidth > logView.maxLineWidth)
                                logView.maxLineWidth = implicitWidth
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: root.logBridge
        function onTextWritten(text, streamName) {
            root.appendText(text, streamName)
        }
    }
}
