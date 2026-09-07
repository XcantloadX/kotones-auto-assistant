import QtQuick
import QtQuick.Layouts
import EuiShell

// 偏好 section：全局快捷键。
ColumnLayout {
    id: root

    property var prefsCtrl

    function _get(path) {
        var parts = path.split('.')
        var obj = root.prefsCtrl ? root.prefsCtrl.config : {}
        for (var i = 0; i < parts.length; i++) {
            if (obj === undefined || obj === null) return undefined
            obj = obj[parts[i]]
        }
        return obj
    }

    FormGroupBox {
        title: "快捷键"
        Layout.fillWidth: true

        HotkeyField {
            label: "启动脚本"
            value: root._get("hotkeys.start") || ""
            onUserCommitted: { root.prefsCtrl.setField("hotkeys.start", newValue) }
        }

        HotkeyField {
            label: "停止脚本"
            value: root._get("hotkeys.stop") || ""
            onUserCommitted: { root.prefsCtrl.setField("hotkeys.stop", newValue) }
        }
    }
}
