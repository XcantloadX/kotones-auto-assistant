import QtQuick
import QtQuick.Layouts
import EuiShell

// 偏好 section：程序更新。
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
        title: "更新"
        Layout.fillWidth: true

        FormComboBox {
            label: "检查更新时机"
            value: root._get("misc.check_update") || "startup"
            options: [
                { label: "从不", value: "never" },
                { label: "启动时", value: "startup" }
            ]
            onUserSelected: function(v) { root.prefsCtrl.setField("misc.check_update", v) }
        }

        FormCheckBox {
            label: "自动安装更新"
            value: root._get("misc.auto_install_update") === true
            onUserToggled: function(checked) { root.prefsCtrl.setField("misc.auto_install_update", checked) }
        }

        FormComboBox {
            label: "更新通道"
            value: root._get("misc.update_channel") || "release"
            options: [
                { label: "稳定版", value: "release" },
                { label: "测试版", value: "beta" }
            ]
            onUserSelected: function(v) { root.prefsCtrl.setField("misc.update_channel", v) }
        }
    }
}
