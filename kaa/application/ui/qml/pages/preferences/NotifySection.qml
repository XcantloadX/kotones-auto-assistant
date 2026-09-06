import QtQuick
import QtQuick.Layouts
import EuiShell

// 偏好 section：通知（系统通知 / 推送通知）。
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
        title: "通知"
        Layout.fillWidth: true

        FormCheckBox {
            label: "系统通知"
            value: root._get("notify.system") === true
            onUserToggled: function(checked) { root.prefsCtrl.setField("notify.system", checked) }
        }

        FormCheckBox {
            label: "推送通知"
            value: root._get("notify.push.enabled") === true
            onUserToggled: function(checked) { root.prefsCtrl.setField("notify.push.enabled", checked) }
        }

        FormComboBox {
            label: "推送类型"
            visible: root._get("notify.push.enabled") === true
            value: root._get("notify.push.type") || "custom"
            options: [
                { label: "自定义命令", value: "custom" },
                { label: "Discord Webhook", value: "discord" },
            ]
            onUserSelected: function(v) {
                root.prefsCtrl.setField("notify.push.type", v)
                if (v === "discord") {
                    root.prefsCtrl.setField("notify.push.command", "")
                } else {
                    root.prefsCtrl.setField("notify.push.webhook_url", "")
                }
            }
        }

        FormTextField {
            label: "自定义命令"
            placeholder: "任务完成后执行的命令"
            visible: root._get("notify.push.enabled") === true && root._get("notify.push.type") === "custom"
            value: root._get("notify.push.command") || ""
            onUserEdited: function(v) { root.prefsCtrl.setField("notify.push.command", v) }
        }

        FormTextField {
            label: "Webhook URL"
            placeholder: "https://discord.com/api/webhooks/..."
            visible: root._get("notify.push.enabled") === true && root._get("notify.push.type") === "discord"
            value: root._get("notify.push.webhook_url") || ""
            onUserEdited: function(v) { root.prefsCtrl.setField("notify.push.webhook_url", v) }
        }
    }
}
