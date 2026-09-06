import QtQuick
import QtQuick.Layouts
import EuiShell

// 偏好 section：数据收集（匿名上报）。
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
        title: "数据收集"
        Layout.fillWidth: true

        FormCheckBox {
            label: "自动发送匿名错误报告"
            value: root._get("telemetry.sentry") === true
            onUserToggled: function(checked) { root.prefsCtrl.setField("telemetry.sentry", checked) }
        }

        FormCheckBox {
            label: "错误上报时附带截图"
            value: root._get("telemetry.upload_screenshot") === true
            onUserToggled: function(checked) { root.prefsCtrl.setField("telemetry.upload_screenshot", checked) }
        }

        FormCheckBox {
            label: "匿名收集统计数据"
            value: root._get("telemetry.statics") === true
            onUserToggled: function(checked) { root.prefsCtrl.setField("telemetry.statics", checked) }
        }
    }
}
