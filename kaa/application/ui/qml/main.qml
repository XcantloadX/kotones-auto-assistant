import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"
import "dialogs"

ApplicationWindow {
    id: window
    title: "琴音小助手"
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

    SystemPalette { id: sysPalette }
    color: sysPalette.window
    flags: Qt.platform.os === "windows"
        ? (Qt.Window | Qt.FramelessWindowHint)
        : Qt.Window

    FontLoader {
        source: "file:///" + fluentFontPath
    }

    // ── Per-tab 数据模型 ──────────────────────────────────────────
    property var tabList: []
    property int activeTabIndex: 0
    property bool prefsMode: false
    property int _prevTitleBarIndex: 0
    property bool allowImmediateClose: false
    property var activeSettingsCtrl: null
    property var activeProduceCtrl: null

    function _onTabsChanged() {
        tabList = JSON.parse(TabManager.tabsJson())
        activeTabIndex = TabManager.activeTabIndex
        activeSettingsCtrl = TabManager.activeSettingsController
        activeProduceCtrl = TabManager.activeProduceController
        if (tabList.length === 0) titleBar.setCurrentIndex(0)
        else if (activeTabIndex >= 0) titleBar.setCurrentIndex(1)
    }

    function _onActiveTabChanged() {
        activeTabIndex = TabManager.activeTabIndex
        activeSettingsCtrl = TabManager.activeSettingsController
        activeProduceCtrl = TabManager.activeProduceController
        if (activeTabIndex < 0) titleBar.setCurrentIndex(0)
    }

    function enterPrefsMode() {
        _prevTitleBarIndex = titleBar.currentIndex
        titleBar.setCurrentIndex(1)
        prefsMode = true
    }

    function exitPrefsMode() {
        prefsMode = false
        titleBar.setCurrentIndex(_prevTitleBarIndex)
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
        target: splash
        function onShowChangelogDialog(version, text) {
            changelogDialog.changelogVersion = version
            changelogDialog.changelogText = text
            changelogDialog.open()
        }
    }

    Connections {
        target: splash
        function onShowMigrationDialog(messages) {
            migrationDialog.messages = messages
            migrationDialog.open()
        }
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
                color: sysPalette.windowText
                wrapMode: Text.Wrap
                width: parent.width
                lineHeight: 1.4
            }
        }

        footer: Rectangle {
            implicitHeight: 81
            color: sysPalette.window
            Rectangle {
                width: parent.width; height: 1
                color: Application.styleHints.colorScheme === Qt.Light ? "#0F000000" : "#15FFFFFF"
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

    Dialog {
        id: changelogDialog
        property string changelogVersion: ""
        property string changelogText: ""
        title: "更新日志（v" + changelogVersion + "）"
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, window.width - 80)
        height: Math.min(420, window.height - 120)
        standardButtons: Dialog.Ok
        onAccepted: splash.onChangelogDismissed()
        onRejected: splash.onChangelogDismissed()

        ScrollView {
            anchors.fill: parent; clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn
            Text {
                width: changelogDialog.width - 48
                text: changelogDialog.changelogText
                wrapMode: Text.Wrap; font.pixelSize: 14; lineHeight: 1.5
                color: sysPalette.windowText
            }
        }
    }

    Dialog {
        id: migrationDialog
        property var messages: []
        title: "配置升级报告"
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, window.width - 80)
        height: Math.min(420, window.height - 120)
        standardButtons: Dialog.Ok

        ScrollView {
            anchors.fill: parent; clip: true
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            Column {
                width: migrationDialog.width - 48; spacing: 8; topPadding: 8; bottomPadding: 8
                Repeater {
                    model: migrationDialog.messages
                    delegate: Row {
                        spacing: 6; width: parent.width
                        Text {
                            text: modelData.level === "warning" ? "⚠️" : "ℹ️"
                            font.pixelSize: 13
                            color: modelData.level === "warning" ? "#e65100" : sysPalette.windowText
                            verticalAlignment: Text.AlignTop
                        }
                        Text {
                            width: parent.width - 26
                            text: {
                                var vi = ""
                                if (modelData.oldVersion && modelData.newVersion)
                                    vi = "（" + modelData.oldVersion + " → " + modelData.newVersion + "）"
                                return vi + modelData.text
                            }
                            wrapMode: Text.Wrap; font.pixelSize: 13; lineHeight: 1.4
                            color: sysPalette.windowText
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
        settingsCtrl: window.activeSettingsCtrl
        produceCtrl: window.activeProduceCtrl
    }

    // ── 主内容区（Splash 隐藏后显示） ──────────────────────────
    ColumnLayout {
        visible: splash.ready
        anchors.fill: parent
        spacing: 0

        TitleBar {
            id: titleBar
            Layout.fillWidth: true
            configManagerDialog: configManagerDialog
            prefsMode: window.prefsMode
            onSettingsRequested: window.enterPrefsMode()
            onBackRequested: window.exitPrefsMode()
            onMinimizeRequested: window.showMinimized()
            onCloseRequested: window.requestAppClose()
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: titleBar.currentIndex

            // ── index 0: 总览页 ────────────────────────────
            OverviewPage {
                configManagerDialog: configManagerDialog
            }

            // ── index 1: per-tab 内容区 ─────────────────────
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
                            runCtrl: TabManager.runCtrlAt(index)
                            settingsCtrl: TabManager.settingsCtrlAt(index)
                            progressCtrl: TabManager.progressBridgeAt(index)
                            logBridge: TabManager.logBridgeAt(index)
                            produceCtrl: TabManager.produceCtrlAt(index)
                            updateCtrl: TabManager.updateCtrlAt(index)
                            feedbackCtrl: TabManager.feedbackCtrlAt(index)
                            navigation: navigation
                            prefsMode: window.prefsMode
                        }
                    }
                }

                // ── prefsMode 覆盖层 ────────────────
                Rectangle {
                    anchors.fill: parent
                    visible: window.prefsMode
                    color: sysPalette.window
                    Label {
                        anchors.centerIn: parent
                        text: "偏好设置"
                        font.pixelSize: 16
                        opacity: 0.6
                    }
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

    ConfigManagerDialog {
        id: configManagerDialog
        tabManager: TabManager
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

