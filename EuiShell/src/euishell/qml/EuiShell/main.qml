import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: window
    title: splash.appName
    width: 1100
    height: 680
    visible: true
    minimumWidth: 800
    minimumHeight: 600
    font.family: Qt.platform.os === "windows"
        ? "Microsoft YaHei UI"
        : Qt.platform.os === "osx"
            ? "PingFang SC"
            : "Noto Sans CJK SC"

    color: palette.window
    flags: Qt.platform.os === "windows"
        ? (Qt.Window | Qt.FramelessWindowHint)
        : Qt.Window

    FontLoader {
        source: fluentFontPath
    }

    // ── Per-tab 数据模型 ──────────────────────────────────────────
    property var tabList: []
    property int activeTabIndex: 0
    property string fullscreenMode: ""  // "" / "preferences" / 注册的全屏页面 id
    property int _prevTitleBarIndex: 0
    property bool allowImmediateClose: false
    property var activeTabCtrl: null

    // 全屏页面注册表（preferences 内置 + 下游注册）
    readonly property var fullscreenPages: {
        var pages = [{ id: "preferences", url: Qt.resolvedUrl("pages/PreferencesPage.qml").toString() }]
        var registered = JSON.parse(ShellRegistry.fullscreenPagesJson())
        for (var i = 0; i < registered.length; i++) pages.push(registered[i])
        return pages
    }
    readonly property bool hasOverview: ShellRegistry.hasOverview()
    // tab 内容区在 StackLayout 中的下标（无总览时前移一位）
    readonly property int tabIndex: hasOverview ? 1 : 0

    function _onTabsChanged() {
        tabList = JSON.parse(TabManager.tabsJson())
        activeTabIndex = TabManager.activeTabIndex
        activeTabCtrl = TabManager.activeTabController
        if (tabList.length === 0) titleBar.setCurrentIndex(0)
        else if (activeTabIndex >= 0) titleBar.setCurrentIndex(tabIndex)
    }

    function _onActiveTabChanged() {
        activeTabIndex = TabManager.activeTabIndex
        activeTabCtrl = TabManager.activeTabController
        if (activeTabIndex < 0) titleBar.setCurrentIndex(0)
    }

    function enterFullscreenMode(mode) {
        _prevTitleBarIndex = titleBar.currentIndex
        titleBar.setCurrentIndex(tabIndex)
        fullscreenMode = mode
    }

    function exitFullscreenMode() {
        fullscreenMode = ""
        titleBar.setCurrentIndex(_prevTitleBarIndex)
    }

    function minimizeWindow() {
        if (Qt.platform.os === "windows")
            windowStateBridge.minimize()
        else
            window.showMinimized()
    }

    function requestAppClose() {
        var anyRunning = TabManager.anyRunning
        var closeRunner = function() {
            window.allowImmediateClose = true
            window.close()
        }
        if (anyRunning) {
            taskErrorDialog.mainInstruction = "确认退出"
            taskErrorDialog.content = "当前仍在执行任务，确定要退出吗？退出将先停止任务。"
            taskErrorDialog.buttons = [
                { id: "cancel",  text: "取消" },
                { id: "confirm", text: "退出", highlighted: true }
            ]
            taskErrorDialog.open()
            return
        }
        navigation.requestGuardedAction("关闭窗口", closeRunner)
    }

    Connections {
        target: errorDialog
        function onShowDialog(mainInstruction, content, buttons) {
            taskErrorDialog.mainInstruction = mainInstruction
            taskErrorDialog.content = content
            taskErrorDialog.buttons = buttons
            taskErrorDialog.open()
        }
    }

    Dialog {
        id: taskErrorDialog
        property string mainInstruction: ""
        property string content: ""
        property var buttons: []

        title: taskErrorDialog.mainInstruction
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: Math.min(480, window.width - 80)
        standardButtons: Dialog.NoButton

        Column {
            width: parent.width
            spacing: 8
            Text {
                text: taskErrorDialog.content
                font.pixelSize: 13
                color: palette.windowText
                wrapMode: Text.Wrap
                width: parent.width
                lineHeight: 1.4
            }
        }

        footer: Rectangle {
            implicitHeight: 81
            color: palette.window
            Rectangle {
                width: parent.width; height: 1
                color: AppTheme.isDark ? "#15FFFFFF" : "#0F000000"
            }
            Row {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 24; spacing: 8
                Repeater {
                    model: taskErrorDialog.buttons
                    Button {
                        text: modelData.text
                        highlighted: index === taskErrorDialog.buttons.length - 1
                        onClicked: {
                            if (modelData.id === "confirm") {
                                // 关闭确认：通过守卫检查未保存更改
                                taskErrorDialog.close()
                                navigation.requestGuardedAction("关闭窗口", function() {
                                    window.allowImmediateClose = true
                                    window.close()
                                })
                            } else if (modelData.id !== undefined) {
                                errorDialog.onButtonClicked(modelData.id)
                                taskErrorDialog.close()
                            } else {
                                taskErrorDialog.close()
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Splash（启动时显示） ─────────────────────────────────────
    SplashOverlay { visible: !splash.ready }

    // ── NavigationCoordinator（页面切换守卫，不可见） ──────────
    NavigationCoordinator {
        id: navigation
        unsavedChangesDialog: unsavedChangesDialog
        tabGuards: window.activeTabCtrl ? window.activeTabCtrl.dirtyGuards : []
        onFullscreenModeRequested: window.enterFullscreenMode(mode)
    }

    // ── 主内容区（Splash 隐藏后显示） ──────────────────────────
    ColumnLayout {
        visible: splash.ready
        anchors.fill: parent
        spacing: 0

        TitleBar {
            id: titleBar
            Layout.fillWidth: true
            configManagerDialog: profileManagerDialog
            fullscreenMode: window.fullscreenMode
            onSettingsRequested: window.enterFullscreenMode("preferences")
            onBackRequested: window.exitFullscreenMode()
            onMinimizeRequested: window.minimizeWindow()
            onCloseRequested: window.requestAppClose()
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: titleBar.currentIndex

            // ── index 0: 总览页（下游 slot；未注册时无此页）───
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: window.hasOverview

                SlotHost {
                    anchors.fill: parent
                    slotName: SlotName.overviewContent
                    fill: true
                }
            }

            // ── index tabIndex: per-tab 内容区 ──────────────
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                StackLayout {
                    anchors.fill: parent
                    currentIndex: window.activeTabIndex

                    Repeater {
                        model: window.tabList
                        delegate: TabContent {
                            required property int index
                            tab: TabManager.tabControllerAt(index)
                            navigation: navigation
                            fullscreenMode: window.fullscreenMode
                        }
                    }
                }
            }
        }
    }

    // ── 全屏模式覆盖层（preferences + 下游注册页面）────────────
    Item {
        anchors.fill: parent
        visible: splash.ready && window.fullscreenMode !== ""

        Repeater {
            model: window.fullscreenPages
            delegate: Loader {
                required property var modelData
                anchors.fill: parent
                visible: window.fullscreenMode === modelData.id

                Component.onCompleted: {
                    // preferences 需要注入 prefsCtrl；其余页面按需在 onLoaded 补充可选属性
                    if (modelData.id === "preferences")
                        setSource(modelData.url, { "prefsCtrl": PreferencesController })
                    else
                        setSource(modelData.url, {})
                }
                onLoaded: {
                    if (item && item.hasOwnProperty("navigation"))
                        item.navigation = navigation
                }
            }
        }
    }

    // ── 未保存更改确认对话框 ──────────────────────────────────
    Dialog {
        id: unsavedChangesDialog
        modal: true
        title: "未保存的更改"
        standardButtons: Dialog.NoButton
        width: 420
        anchors.centerIn: Overlay.overlay

        property string actionLabel: "继续此操作"

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "当前有未保存的更改。在继续" + unsavedChangesDialog.actionLabel + "之前，请保存或放弃。"
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
                Button {
                    text: "取消"
                    onClicked: {
                        navigation.clearPendingGuardedAction()
                        unsavedChangesDialog.close()
                    }
                }
                Button {
                    text: "放弃并继续"
                    onClicked: {
                        unsavedChangesDialog.close()
                        navigation.discardAndContinuePendingAction()
                    }
                }
                Button {
                    text: "保存并继续"
                    highlighted: true
                    onClicked: {
                        unsavedChangesDialog.close()
                        navigation.saveAndContinuePendingAction()
                    }
                }
            }
        }
    }

    ProfileManagerDialog {
        id: profileManagerDialog
        tabManager: TabManager
    }

    NoticeHost {
        id: noticeHost
    }

    // ── 下游窗口级对话框 / 非可视组件 slot ────────────────────
    Item {
        SlotHost {
            slotName: SlotName.windowDialogs
        }
    }

    onClosing: function(close) {
        if (window.allowImmediateClose) {
            window.allowImmediateClose = false
            close.accepted = true
            return
        }
        close.accepted = false
        requestAppClose()
    }

    Component.onCompleted: {
        _onTabsChanged()
        TabManager.tabsChanged.connect(window._onTabsChanged)
        TabManager.activeTabChanged.connect(window._onActiveTabChanged)
    }
}
