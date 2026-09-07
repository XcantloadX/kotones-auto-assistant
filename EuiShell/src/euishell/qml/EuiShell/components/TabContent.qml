import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import ".."
import "../pages"

// 单 tab 内容容器：SideNavigationBar + StackLayout（内置页面 + 下游 pages）。
// 页面统一契约：required property var tab / property var navigation / property string fullscreenMode。
Item {
    id: root

    required property var tab
    property var navigation: null
    property string fullscreenMode: ""

    // 下游扩展点（由 EuiShellApp 透传；组件默认值为空，直接构造亦可加载）
    property list<EuiPageSpec> pages: []
    property Component controlNotices: null
    property Component controlRunExtras: null
    property Component controlFooter: null
    property Component aboutExtra: null
    property list<EuiSectionSpec> settingsSections: []
    property list<EuiLink> aboutLinks: []

    Connections {
        target: TabManager
        function onCapturePageRequested(navIndex) { sideNav.currentIndex = navIndex }
    }

    // 侧边导航模型：内置页 + 下游页面标题 + 内置尾页，与 StackLayout 子项顺序一致
    readonly property var pageTitles: {
        var titles = ["控制", "任务", "设置"]
        for (var i = 0; i < root.pages.length; i++)
            titles.push(root.pages[i].title)
        titles.push("日志")
        titles.push("关于")
        return titles
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideNavigationBar {
            id: sideNav
            Layout.fillHeight: true
            visible: root.fullscreenMode === ""
            model: root.pageTitles

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
            visible: root.fullscreenMode === ""
            currentIndex: sideNav.currentIndex

            ControlPage {
                id: controlPage
                tab: root.tab
                navigation: root.navigation
                fullscreenMode: root.fullscreenMode
                controlNotices: root.controlNotices
                controlRunExtras: root.controlRunExtras
                controlFooter: root.controlFooter
            }
            TaskPage {
                id: taskPage
                tab: root.tab
                navigation: root.navigation
                fullscreenMode: root.fullscreenMode
            }
            SettingsPage {
                id: settingsPage
                tab: root.tab
                navigation: root.navigation
                fullscreenMode: root.fullscreenMode
                settingsSections: root.settingsSections
            }

            // ── 下游自定义页面（按声明顺序，位于设置页之后、日志页之前）──
            Repeater {
                model: root.pages
                delegate: Loader {
                    required property var modelData
                    sourceComponent: modelData.source
                    onLoaded: {
                        // 页面根元素按契约声明可选注入属性，挂载时回填
                        if (item && item.hasOwnProperty("tab")) item.tab = root.tab
                        if (item && item.hasOwnProperty("navigation")) item.navigation = root.navigation
                        if (item && item.hasOwnProperty("fullscreenMode")) item.fullscreenMode = root.fullscreenMode
                    }
                }
            }

            LogPage {
                id: logPage
                tab: root.tab
                navigation: root.navigation
                fullscreenMode: root.fullscreenMode
            }
            AboutPage {
                id: aboutPage
                tab: root.tab
                navigation: root.navigation
                fullscreenMode: root.fullscreenMode
                aboutExtra: root.aboutExtra
                aboutLinks: root.aboutLinks
            }
        }
    }
}
