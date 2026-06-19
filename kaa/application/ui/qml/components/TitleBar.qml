import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

// 主窗口标题栏：TabStrip + PageHeader（双模式）+ WindowControls。
Item {
    id: root

    readonly property int _stripH: 8   // 顶部纯拖拽条高度
    readonly property int _tabH: 34    // tab 行高度
    height: _stripH + _tabH

    readonly property color _titleBg: Application.styleHints.colorScheme === Qt.Light ? "#f3f3f3" : "#202020"
    readonly property color _hover:    Application.styleHints.colorScheme === Qt.Light ? Qt.rgba(0,0,0,0.08) : Qt.rgba(1,1,1,0.08)
    readonly property color _hoverStrong: Application.styleHints.colorScheme === Qt.Light ? Qt.rgba(0,0,0,0.15) : Qt.rgba(1,1,1,0.15)
    readonly property color _fg:       Application.styleHints.colorScheme === Qt.Light ? "#000000" : "#ffffff"
    readonly property color _tabCardBg: Application.styleHints.colorScheme === Qt.Light ? "#ffffff" : "#2d2d2d"

    required property var configManagerDialog

    readonly property int currentIndex: tabStrip.currentIndex
    property bool prefsMode: false

    function setCurrentIndex(index) {
        tabStrip.currentIndex = index
    }

    signal settingsRequested()
    signal backRequested()
    signal minimizeRequested()
    signal closeRequested()

    property var _tabs: []
    function _reloadTabs() {
        root._tabs = JSON.parse(TabManager.tabsJson())
    }
    Component.onCompleted: _reloadTabs()

    // ── 同步 tab 交互区右边界给 Win32 hit-test ─────────
    Binding {
        target: (typeof tabBarBridge !== "undefined") ? tabBarBridge : null
        property: "tabInteractiveEnd"
        value: tabStrip.interactiveEnd
        when: !root.prefsMode
    }

    Connections {
        target: TabManager
        function onTabsChanged()      { root._reloadTabs() }
        function onActiveTabChanged() { root._reloadTabs() }
        function onCloseTabBlocked(reason) { /* show notice in future */ }
        function onReadyToCloseTab(index) {
            TabManager.closeTab(index)
        }
    }

    // ── 背景 ────────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: root._titleBg
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 顶部纯拖拽条（HTCAPTION 区域）
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root._stripH

            MouseArea {
                anchors.fill: parent
                onPressed: function(event) {
                    event.accepted = true
                    ApplicationWindow.window.startSystemMove()
                }
            }
        }

        // Tab 行内容区（两种子组件叠放，visibility 切换）
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: root._tabH

            TabStrip {
                id: tabStrip
                anchors.fill: parent
                visible: !root.prefsMode
                configManagerDialog: root.configManagerDialog
                tabs: root._tabs
                onSettingsRequested: root.settingsRequested()
            }

            PageHeader {
                id: pageHeader
                anchors.fill: parent
                visible: root.prefsMode
                title: "琴音小助手"
                iconSource: "file:///" + splash.iconPath
                onBackRequested: root.backRequested()
            }
        }
    }

    // 窗口控件贴右侧，覆盖完整 TitleBar 高度（含顶部拖拽条）
    WindowControls {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        window: root.Window.window
        onMinimizeRequested: root.minimizeRequested()
        onCloseRequested: root.closeRequested()
    }
}
