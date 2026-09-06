import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "../pages"

// 单 tab 内容容器：SideNavigationBar + StackLayout（内置页面 + 自定义页面）。
// 页面统一契约：required property var tab / property var navigation / property string fullscreenMode。
Item {
    id: root

    required property var tab
    property var navigation: null
    property string fullscreenMode: ""

    Connections {
        target: TabManager
        function onCapturePageRequested(navIndex) { sideNav.currentIndex = navIndex }
    }

    // 自定义页面列表（registry 注册，after 仅支持自定义页面 id 排序）
    readonly property var customPages: JSON.parse(ShellRegistry.customPagesJson())

    // 侧边导航模型：内置页 + 自定义页标题 + 内置尾页，与 StackLayout 子项顺序一致
    readonly property var pageTitles: {
        var titles = ["控制", "任务", "设置"]
        for (var i = 0; i < root.customPages.length; i++)
            titles.push(root.customPages[i].title)
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
            }

            // ── 下游自定义页面（按注册顺序，位于设置页之后、日志页之前）──
            Repeater {
                model: root.customPages
                delegate: Loader {
                    required property var modelData
                    sourceComponent: null
                    Component.onCompleted: {
                        // 自定义页面统一契约：tab / navigation / fullscreenMode
                        setSource(modelData.url, {
                            "tab": root.tab,
                            "navigation": root.navigation,
                            "fullscreenMode": root.fullscreenMode
                        })
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
            }
        }
    }
}
