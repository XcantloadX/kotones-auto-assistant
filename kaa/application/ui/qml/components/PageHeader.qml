import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".." as App

// 独立页面的标题行：返回按钮 + 图标 + 标题文本 + 可拖动填充区。
// 由 TitleBar 在全屏模式时切入。
Item {
    id: root

    property string title: ""
    property string iconSource: ""

    signal backRequested()

    // 供 TitleBar 同步给 Win32 hit-test：返回按钮右边界即交互区终点
    readonly property real interactiveEnd: backBtn.width + 4

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ── 返回按钮 ──────────────────────────────────────────
        Item {
            id: backBtn
            Layout.preferredWidth: 40
            Layout.fillHeight: true

            HoverHandler { id: backHover }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 4
                radius: 5
                color: backHover.hovered ? App.AppTheme.hover : "transparent"
            }

            FluentIcon {
                anchors.centerIn: parent
                glyph: App.FluentIcons.chevron_left_20_regular
                font.pixelSize: 13
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.backRequested()
                onPressed: event => event.accepted = true
            }
        }

        // ── 图标 + 标题（其余区域均可拖动窗口）────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            MouseArea {
                anchors.fill: parent
                onPressed: function(event) {
                    event.accepted = true
                    ApplicationWindow.window.startSystemMove()
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 6
                spacing: 10

                Item {
                    width: 16; height: 16

                    Image {
                        anchors.fill: parent
                        source: root.iconSource
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        visible: status === Image.Ready
                    }
                }

                Text {
                    text: root.title
                    color: App.AppTheme.fg
                    font.pixelSize: 12
                }
            }
        }
    }
}
