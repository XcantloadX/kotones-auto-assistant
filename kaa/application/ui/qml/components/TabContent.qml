import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "../pages"

// 单 tab 内容容器：SideNavigationBar + StackLayout（多页面切换）
Item {
    id: root

    required property var runCtrl
    property var settingsCtrl: null
    property var progressCtrl: null
    property var logBridge: null
    property var produceCtrl: null
    property var updateCtrl: null
    property var feedbackCtrl: null
    property var navigation: null
    property bool prefsMode: false

    Connections {
        target: TabManager
        function onCapturePageRequested(navIndex) { sideNav.currentIndex = navIndex }
    }

    readonly property int sideNavIndex: sideNav.currentIndex

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideNavigationBar {
            id: sideNav
            Layout.fillHeight: true
            visible: !root.prefsMode
            model: ["控制", "任务", "设置", "方案", "更新", "日志", "反馈"]

            onCurrentChanging: function(index, previousIndex) {
                if (root.navigation) {
                    root.navigation.requestGuardedAction("切换页面", function() {
                        sideNav.confirmSwitch(index)
                    })
                } else {
                    sideNav.confirmSwitch(index)
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !root.prefsMode
            currentIndex: sideNav.currentIndex

            ControlPage  { id: controlPage;   runCtrl: root.runCtrl; progressCtrl: root.progressCtrl; keepScreenshots: (root.settingsCtrl?.config?.profile?.keep_screenshots) ?? false }
            TaskPage     { id: taskPage;      runCtrl: root.runCtrl }
            SettingsPage { id: settingsPage;  settingsCtrl: root.settingsCtrl; runCtrl: root.runCtrl }
            ProducePage  { id: producePage;   produceCtrl: root.produceCtrl }
            UpdatePage   { id: updatePage;    updateCtrl: root.updateCtrl }
            LogPage      { id: logPage;       logBridge: root.logBridge }
            FeedbackPage { id: feedbackPage;  feedbackCtrl: root.feedbackCtrl }
        }
    }
}
