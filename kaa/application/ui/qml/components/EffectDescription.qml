import QtQuick
import QtQuick.Controls
import ".." as App

// 对齐 hatsuboshi EffectDescription：
// segments: [{kind, text, icon?, bg?, stamina?, tone?}, ...]
// kind: text | buff | highlight | break
Item {
    id: root

    property var segments: []
    property var staticIcons: ({})
    property real fontSize: 13
    property real iconSize: 18

    // 将 flat tokens 拆成行（遇 break 换行）
    readonly property var _lines: {
        var lines = []
        var cur = []
        var segs = root.segments || []
        for (var i = 0; i < segs.length; i++) {
            var s = segs[i]
            if (!s) continue
            if (s.kind === "break") {
                if (cur.length > 0) lines.push(cur)
                cur = []
            } else {
                cur.push(s)
            }
        }
        if (cur.length > 0) lines.push(cur)
        return lines
    }

    implicitWidth: col.implicitWidth
    implicitHeight: col.implicitHeight
    width: parent ? parent.width : implicitWidth
    height: col.implicitHeight

    Column {
        id: col
        width: parent.width
        spacing: 4

        Repeater {
            model: root._lines

            // 每一行用 Flow 自动折行
            Flow {
                required property var modelData
                width: col.width
                spacing: 2

                Repeater {
                    model: modelData

                    delegate: Item {
                        id: tok
                        required property var modelData
                        readonly property string kind: modelData.kind || "text"
                        readonly property string txt: modelData.text || ""

                        // buff 胶囊
                        visible: kind === "buff" || kind === "text" || kind === "highlight"
                        clip: kind === "buff"
                        width: Math.min(
                            kind === "buff" ? buffRow.implicitWidth + 6 : txtItem.implicitWidth,
                            col.width
                        )
                        height: Math.max(root.iconSize, root.fontSize + 4)

                        // ── buff chip ──────────────────────────
                        Rectangle {
                            visible: tok.kind === "buff"
                            anchors.fill: parent
                            radius: 4
                            color: App.AppTheme.isDark ? "#414145" : "#ebecfa"

                            Row {
                                id: buffRow
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 2
                                spacing: 1

                                // 效果图标 or 体力图标
                                Item {
                                    width: root.iconSize
                                    height: root.iconSize
                                    visible: !!(tok.modelData.stamina) || !!(tok.modelData.icon)

                                    // 体力
                                    Image {
                                        visible: !!(tok.modelData.stamina)
                                        anchors.fill: parent
                                        source: root.staticIcons.stamina
                                            ? "file:///" + root.staticIcons.stamina : ""
                                        fillMode: Image.PreserveAspectFit
                                        mipmap: true
                                        cache: true
                                    }

                                    // exam effect
                                    ExamEffectIcon {
                                        visible: !tok.modelData.stamina && !!(tok.modelData.icon)
                                        anchors.fill: parent
                                        iconPath: tok.modelData.icon || ""
                                        bgPath: tok.modelData.bg || ""
                                    }
                                }

                                Text {
                                    text: tok.txt
                                    font.pixelSize: root.fontSize
                                    color: palette.windowText
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }

                        // ── plain / highlight text ─────────────
                        Text {
                            id: txtItem
                            visible: tok.kind === "text" || tok.kind === "highlight"
                            anchors.verticalCenter: parent.verticalCenter
                            text: tok.txt
                            width: parent.width
                            font.pixelSize: root.fontSize
                            wrapMode: Text.WordWrap
                            color: {
                                if (tok.kind === "highlight") {
                                    // sky-500 / sky-600
                                    return tok.modelData.tone === "desc" ? "#0284c7" : "#0ea5e9"
                                }
                                return palette.windowText
                            }
                        }
                    }
                }
            }
        }
    }
}
