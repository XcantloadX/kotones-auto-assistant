import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import ".." as App

// 主窗口标题栏：TabStrip + PageHeader（双模式）+ WindowControls。
Item {
    id: root

    readonly property int _stripH: 8   // 顶部纯拖拽条高度
    readonly property int _tabH: 34    // tab 行高度
    height: _stripH + _tabH

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

    // 待关闭 tab 的 index（dirty 检查用）
    property int pendingCloseIndex: -1

    property var _tabs: []
    function _reloadTabs() {
        root._tabs = JSON.parse(TabManager.tabsJson())
    }
    Component.onCompleted: _reloadTabs()

    // ── 同步交互区右边界给 Win32 hit-test ─────────
    Binding {
        target: (typeof tabBarBridge !== 'undefined' && tabBarBridge) ? tabBarBridge : null
        property: "tabInteractiveEnd"
        value: root.prefsMode ? pageHeader.interactiveEnd : tabStrip.interactiveEnd
    }

    Connections {
        target: TabManager
        function onTabsChanged()      { root._reloadTabs() }
        function onActiveTabChanged() { root._reloadTabs() }
        function onCloseTabBlocked(reason) { /* show notice in future */ }
        function onReadyToCloseTab(index) {
            root.pendingCloseIndex = index
            var sc = TabManager.settingsCtrlAt(index)
            var pc = TabManager.produceCtrlAt(index)
            var dirty = (sc && sc.isDirty()) || (pc && pc.isDirty())
            if (dirty) {
                tabCloseUnsavedDialog.open()
            } else {
                TabManager.closeTab(index)
                root.pendingCloseIndex = -1
            }
        }
    }

    // ── 背景 ────────────────────────────────────────────────────
    // 颜色由 AppTheme 统一管理（避免散落的 palette / colorScheme 判断）。
    // prefsMode + 非 solid：全透明，让 Mica/acrylic DWM 背景完整透出。
    Rectangle {
        anchors.fill: parent
        color: (root.prefsMode && !App.AppTheme.isSolid)
            ? "transparent"
            : App.AppTheme.titleBg
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

    // ── Tab 关闭时的 dirty 检查对话框 ──────────────────────────────────
    Dialog {
        id: tabCloseUnsavedDialog
        modal: true
        title: "未保存的更改"
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "该标签页有未保存的更改，关闭前请选择处理方式。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
                Button {
                    text: "取消"
                    onClicked: {
                        tabCloseUnsavedDialog.close()
                        root.pendingCloseIndex = -1
                    }
                }
                Button {
                    text: "不保存并关闭"
                    onClicked: {
                        var idx = root.pendingCloseIndex
                        tabCloseUnsavedDialog.close()
                        root.pendingCloseIndex = -1
                        if (idx >= 0) {
                            TabManager.closeTab(idx)
                        }
                    }
                }
                Button {
                    text: "保存并关闭"
                    highlighted: true
                    onClicked: {
                        var idx = root.pendingCloseIndex
                        tabCloseUnsavedDialog.close()
                        root.pendingCloseIndex = -1
                        if (idx >= 0) {
                            var sc = TabManager.settingsCtrlAt(idx)
                            var pc = TabManager.produceCtrlAt(idx)
                            if (sc && sc.isDirty()) sc.save()
                            if (pc && pc.isDirty()) pc.save()
                            TabManager.closeTab(idx)
                        }
                    }
                }
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
