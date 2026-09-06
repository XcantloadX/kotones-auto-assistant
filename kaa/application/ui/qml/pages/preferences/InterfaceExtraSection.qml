import QtQuick
import QtQuick.Layouts
import EuiShell

// 偏好 section：启动时打开的页面。
ColumnLayout {
    id: root

    required property var prefsCtrl

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
        title: "启动"
        Layout.fillWidth: true

        FormComboBox {
            label: "启动时打开"
            value: root._get("interface.startup_page") || "last_opened"
            options: [
                { label: "总览页面", value: "overview" },
                { label: "上次打开的配置", value: "last_opened" },
            ]
            onUserSelected: function(v) { root.prefsCtrl.setField("interface.startup_page", v) }
        }
    }
}
