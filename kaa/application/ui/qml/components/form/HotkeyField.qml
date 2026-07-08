import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../"

ColumnLayout {
    id: root

    required property string label
    property string value: ""
    property string helpText: ""
    signal userCommitted(string newValue)

    spacing: 4
    property bool recording: false

    function toDisplayText(sequence) {
        if (!sequence) return ""
        var isMac = Qt.platform.os === "osx"
        var s = sequence
        var mods = []
        var checks = [
            ["Ctrl+",  isMac ? "⌃" : "Ctrl+"],
            ["Alt+",   isMac ? "⌥" : "Alt+"],
            ["Meta+",  isMac ? "⌘" : "Win+"],
            ["Shift+", isMac ? "⇧" : "Shift+"],
        ]
        for (var i = 0; i < checks.length; i++) {
            if (s.startsWith(checks[i][0])) {
                mods.push(checks[i][1])
                s = s.substring(checks[i][0].length)
            }
        }
        if (isMac) {
            var sym = {
                "Return": "↩", "Backspace": "⌫", "Del": "⌦",
                "Tab": "⇥", "Escape": "⎋", "Space": "␣",
                "Up": "↑", "Down": "↓", "Left": "←", "Right": "→",
                "Home": "↖", "End": "↘", "PgUp": "⇞", "PgDown": "⇟",
                "Ins": "Ins",
            }
            s = sym[s] !== undefined ? sym[s] : s
        }
        if (isMac) {
            return mods.join("") + s
        } else {
            return mods.join("") + s
        }
    }

    function buildSequence(modifiers, key) {
        var parts = []
        if (modifiers & Qt.ControlModifier) parts.push("Ctrl")
        if (modifiers & Qt.AltModifier)     parts.push("Alt")
        if (modifiers & Qt.MetaModifier)    parts.push("Meta")
        if (modifiers & Qt.ShiftModifier)   parts.push("Shift")
        var name = keyName(key)
        if (!name) return null
        parts.push(name)
        return parts.join("+")
    }

    function keyName(key) {
        if (key >= Qt.Key_F1 && key <= Qt.Key_F35)
            return "F" + (key - Qt.Key_F1 + 1)
        if (key >= Qt.Key_A && key <= Qt.Key_Z)
            return String.fromCharCode(key)
        if (key >= Qt.Key_0 && key <= Qt.Key_9)
            return String.fromCharCode(key)
        var map = {}
        map[Qt.Key_Space]     = "Space"
        map[Qt.Key_Return]    = "Return"
        map[Qt.Key_Enter]     = "Return"
        map[Qt.Key_Tab]       = "Tab"
        map[Qt.Key_Backspace] = "Backspace"
        map[Qt.Key_Delete]    = "Del"
        map[Qt.Key_Insert]    = "Ins"
        map[Qt.Key_Home]      = "Home"
        map[Qt.Key_End]       = "End"
        map[Qt.Key_PageUp]    = "PgUp"
        map[Qt.Key_PageDown]  = "PgDown"
        map[Qt.Key_Left]      = "Left"
        map[Qt.Key_Right]     = "Right"
        map[Qt.Key_Up]        = "Up"
        map[Qt.Key_Down]      = "Down"
        return map[key] || null
    }

    FormField {
        Layout.fillWidth: true
        labelText: root.label
        helpText: root.helpText

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            TextField {
                id: displayField
                Layout.fillWidth: true
                readOnly: true

                text: root.recording
                    ? ""
                    : (root.value ? root.toDisplayText(root.value) : "")
                placeholderText: root.recording ? qsTr("按下快捷键…（按 ESC 取消）") : qsTr("点击设置")

                onActiveFocusChanged: {
                    if (!activeFocus) {
                        root.recording = false
                    }
                }

                Keys.enabled: root.recording
                Keys.onPressed: function(event) {
                    if (!root.recording) return;
                    var modOnly = [
                        Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_Shift,
                        Qt.Key_Super_L, Qt.Key_Super_R, Qt.Key_AltGr,
                    ]
                    if (modOnly.indexOf(event.key) !== -1) {
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Escape) {
                        root.recording = false
                        event.accepted = true
                        return
                    }
                    var seq = root.buildSequence(event.modifiers, event.key)
                    if (seq) {
                        root.userCommitted(seq)
                    }
                    root.recording = false
                    event.accepted = true
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !root.recording
                    hoverEnabled: true
                    cursorShape: Qt.IBeamCursor
                    onClicked: {
                        root.recording = true
                        displayField.forceActiveFocus()
                    }
                }
            }

            Button {
                text: qsTr("清除")
                enabled: !!root.value && !root.recording
                onClicked: root.userCommitted(null)
            }
        }
    }
}
