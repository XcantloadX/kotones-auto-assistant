pragma Singleton
import QtQuick

// Shell 内置 slot 名称常量（与 euishell.plugin.SlotName 保持一致，tests 有同步校验）。
QtObject {
    readonly property string overviewContent: "overview.content"
    readonly property string titlebarTrailing: "titlebar.trailing"
    readonly property string windowDialogs: "window.dialogs"
    readonly property string aboutExtra: "about.extra"
    readonly property string controlRunExtras: "control.runExtras"
    readonly property string controlNotices: "control.notices"
    readonly property string controlFooter: "control.footer"
}
