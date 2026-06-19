import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 总览页：品牌 + 启动按钮 + 配置卡片网格。
Item {
    id: root

    required property var configManagerDialog

    readonly property color _fg:           Application.styleHints.colorScheme === Qt.Light ? "#000000" : "#ffffff"
    readonly property color _hover:        Application.styleHints.colorScheme === Qt.Light ? Qt.rgba(0,0,0,0.06) : Qt.rgba(1,1,1,0.06)
    readonly property color _cardBorder:   Application.styleHints.colorScheme === Qt.Light ? Qt.rgba(0,0,0,0.1) : Qt.rgba(1,1,1,0.1)
    readonly property color _cardBg:       Application.styleHints.colorScheme === Qt.Light ? Qt.rgba(0,0,0,0.03) : Qt.rgba(1,1,1,0.03)
    readonly property color _cardBgHover:  Application.styleHints.colorScheme === Qt.Light ? Qt.rgba(0,0,0,0.06) : Qt.rgba(1,1,1,0.06)

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

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                font.family: "FluentSystemIcons-Regular"
                                font.pixelSize: 17
                                text: seqBtn.isStopMode ? "\uF72A" : "\uF605"
                                color: seqBtn.highlighted ? (Application.styleHints.colorScheme === Qt.Light ? "white" : "black") : root._fg
                            }

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    if (!seqBtn.isStopMode)    return "连续启动"
                                    if (TabManager.stopAllBusy) return "停止中"
                                    return "停止所有"
                                }
                                font.pixelSize: 14
                                color: seqBtn.highlighted ? (Application.styleHints.colorScheme === Qt.Light ? "white" : "black") : root._fg
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

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                font.family: "FluentSystemIcons-Regular"
                                font.pixelSize: 17
                                text: parBtn.isStopMode ? "\uF72A" : "\uF100"
                                color: parBtn.highlighted ? (Application.styleHints.colorScheme === Qt.Light ? "white" : "black") : root._fg
                            }

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    if (!parBtn.isStopMode)    return "并行启动"
                                    if (TabManager.stopAllBusy) return "停止中"
                                    return "停止所有"
                                }
                                font.pixelSize: 14
                                color: parBtn.highlighted ? (Application.styleHints.colorScheme === Qt.Light ? "white" : "black") : root._fg
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
                                ? root._cardBgHover
                                : root._cardBg
                            border.color: root._cardBorder
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
                    text: "还没有创建任何配置"
                    font.pixelSize: 14
                    opacity: 0.7
                }

                Button {
                    highlighted: true
                    text: "创建配置"
                    onClicked: root.configManagerDialog.open()
                }
            }
        }
    }
}
