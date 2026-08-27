import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import ".." as App

// 总览页：品牌 + 启动按钮 + 配置卡片网格。
PageContainer {
    id: root
    showTitle: false
    padding: 0

    required property var configManagerDialog

    property var _allConfigs: []

    function _reload() {
        _allConfigs = JSON.parse(TabManager.allConfigsJson())
    }

    Component.onCompleted: _reload()

    Connections {
        target: TabManager
        function onTabsChanged() { root._reload() }
        function onActiveTabChanged() { root._reload() }
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: scrollView.availableWidth
            spacing: 0

            // ── Brand ─────────────────────────────────────────
            RowLayout {
                Layout.topMargin: 48
                Layout.alignment: Qt.AlignHCenter
                spacing: 14

                Rectangle {
                    width: 80
                    height: 80
                    color: "transparent"

                    Image {
                        anchors.fill: parent
                        source: "file:///" + splash.iconPath
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                ColumnLayout {
                    spacing: 2

                    Label {
                        text: "琴音小助手"
                        font.pixelSize: 30
                        font.weight: Font.DemiBold
                    }

                    Label {
                        text: "v" + splash.appVersion
                        font.pixelSize: 16
                        opacity: 0.65
                    }
                }
            }

            // ── 有配置 ────────────────────────────────────────
            ColumnLayout {
                visible: root._allConfigs.length > 0
                Layout.fillWidth: true
                spacing: 0

                // 启动按钮行
                RowLayout {
                    Layout.topMargin: 28
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 12

                    Button {
                        id: seqBtn
                        readonly property bool isStopMode: TabManager.batchMode === "sequential"
                        highlighted: true
                        enabled: TabManager.batchMode === ""
                                 || (isStopMode && !TabManager.stopAllBusy)
                        implicitWidth: 130
                        onClicked: {
                            if (isStopMode) TabManager.stopAll()
                            else TabManager.startAllSequential()
                        }

                        contentItem: Row {
                            spacing: 7
                            anchors.centerIn: parent

                            FluentIcon {
                                anchors.verticalCenter: parent.verticalCenter
                                glyph: seqBtn.isStopMode
                                    ? App.FluentIcons.stop_20_regular
                                    : App.FluentIcons.play_20_regular
                                font.pixelSize: 17
                                color: seqBtn.highlighted ? (App.AppTheme.isDark ? "black" : "white") : App.AppTheme.fg
                            }

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    if (!seqBtn.isStopMode)    return "连续启动"
                                    if (TabManager.stopAllBusy) return "停止中"
                                    return "停止所有"
                                }
                                font.pixelSize: 14
                                color: seqBtn.highlighted ? (App.AppTheme.isDark ? "black" : "white") : App.AppTheme.fg
                            }
                        }
                    }

                    Button {
                        id: parBtn
                        readonly property bool isStopMode: TabManager.batchMode === "parallel"
                        highlighted: true
                        enabled: TabManager.batchMode === ""
                                 || (isStopMode && !TabManager.stopAllBusy)
                        implicitWidth: 130
                        onClicked: {
                            if (isStopMode) TabManager.stopAll()
                            else TabManager.startAllParallel()
                        }

                        contentItem: Row {
                            spacing: 7
                            anchors.centerIn: parent

                            FluentIcon {
                                anchors.verticalCenter: parent.verticalCenter
                                glyph: parBtn.isStopMode
                                    ? App.FluentIcons.stop_20_regular
                                    : App.FluentIcons.play_multiple_16_regular
                                font.pixelSize: 17
                                color: parBtn.highlighted ? (App.AppTheme.isDark ? "black" : "white") : App.AppTheme.fg
                            }

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    if (!parBtn.isStopMode)    return "并行启动"
                                    if (TabManager.stopAllBusy) return "停止中"
                                    return "停止所有"
                                }
                                font.pixelSize: 14
                                color: parBtn.highlighted ? (App.AppTheme.isDark ? "black" : "white") : App.AppTheme.fg
                            }
                        }
                    }
                }

                // 配置列表
                Label {
                    Layout.topMargin: 28
                    Layout.leftMargin: 40
                    text: "配置"
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    opacity: 0.55
                }

                Flow {
                    Layout.fillWidth: true
                    Layout.topMargin: 10
                    Layout.leftMargin: 32
                    Layout.rightMargin: 32
                    Layout.bottomMargin: 32
                    spacing: 16

                    Repeater {
                        model: root._allConfigs

                        delegate: Rectangle {
                            id: card

                            readonly property int _tabIdx: modelData.tabIndex
                            readonly property bool _isRunning: modelData.isRunning || false

                            width: 260
                            height: contentCol.implicitHeight + 32
                            radius: 8
                            color: cardHover.containsMouse
                                ? App.AppTheme.isDark ? Qt.rgba(1,1,1,0.06) : Qt.rgba(0,0,0,0.06)
                                : App.AppTheme.isDark ? Qt.rgba(1,1,1,0.03) : Qt.rgba(0,0,0,0.03)
                            border.color: App.AppTheme.isDark ? Qt.rgba(1,1,1,0.1) : Qt.rgba(0,0,0,0.1)
                            border.width: 1

                            HoverHandler { id: cardHover }

                            MouseArea {
                                id: cardMouse
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (card._tabIdx < 0) {
                                        TabManager.openTab(modelData.configName)
                                    } else {
                                        TabManager.setActiveTab(card._tabIdx)
                                    }
                                }
                            }

                            ColumnLayout {
                                id: contentCol
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    margins: 16
                                }
                                spacing: 8

                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.configName
                                    font.pixelSize: 15
                                    font.weight: Font.Medium
                                    elide: Text.ElideRight
                                }

                                // 运行状态指示
                                RowLayout {
                                    spacing: 6

                                    Rectangle {
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: card._isRunning ? "#0067c0" : Qt.rgba(0,0,0,0.3)
                                    }

                                    Label {
                                        text: card._isRunning ? "运行中" : "就绪"
                                        font.pixelSize: 12
                                        opacity: 0.7
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── 无配置 ─────────────────────────────────────────
            ColumnLayout {
                visible: root._allConfigs.length === 0
                Layout.fillWidth: true
                Layout.topMargin: 32
                Layout.leftMargin: 40
                Layout.bottomMargin: 32
                spacing: 12

                Label {
                    text: "你还没有创建任何配置"
                    font.pixelSize: 14
                    opacity: 0.7
                }

                Row {
                    spacing: 5

                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "点击"
                        font.pixelSize: 14
                        opacity: 0.7
                    }

                    Button {
                        id: createBtn
                        highlighted: true
                        text: "创建配置"
                        font.pixelSize: 14
                        topPadding: 4
                        bottomPadding: 4
                        leftPadding: 10
                        rightPadding: 10
                        anchors.verticalCenter: parent.verticalCenter
                        onClicked: root.configManagerDialog.open()
                    }

                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "或顶部标签栏的"
                        font.pixelSize: 14
                        opacity: 0.7
                    }

                    Rectangle {
                        width: 22
                        height: 22
                        radius: 4
                        color: App.AppTheme.hover
                        anchors.verticalCenter: parent.verticalCenter

                        FluentIcon {
                            anchors.centerIn: parent
                            glyph: App.FluentIcons.add_20_regular
                            font.pixelSize: 13
                            opacity: 0.7
                        }
                    }

                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "号创建新配置"
                        font.pixelSize: 14
                        opacity: 0.7
                    }
                }
            }
        }
    }
}
