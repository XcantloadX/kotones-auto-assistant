import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EuiShell

// 偏好 section：游戏资源更新。
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
        title: "游戏资源"
        Layout.fillWidth: true

        FormComboBox {
            label: "资源检查时机"
            value: root._get("misc.game_data_check") || "startup"
            options: [
                { label: "手动", value: "manual" },
                { label: "每次启动", value: "startup" },
                { label: "每天一次", value: "daily" },
                { label: "每周一次", value: "weekly" }
            ]
            onUserSelected: function(v) { root.prefsCtrl.setField("misc.game_data_check", v) }
        }

        FormCheckBox {
            label: "自动安装游戏资源更新"
            value: root._get("misc.game_data_auto_update") === true
            onUserToggled: function(checked) { root.prefsCtrl.setField("misc.game_data_auto_update", checked) }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: "立即检查并更新"
                enabled: GameDataCtrl.updateStatus === "idle" || GameDataCtrl.updateStatus === "failed"
                onClicked: GameDataCtrl.triggerUpdate()
            }

            BusyIndicator {
                running: GameDataCtrl.updateStatus === "checking" ||
                         GameDataCtrl.updateStatus === "downloading" ||
                         GameDataCtrl.updateStatus === "building"
                visible: running
                implicitWidth: 20
                implicitHeight: 20
            }

            Label {
                visible: !!GameDataCtrl.progressMessage
                text: GameDataCtrl.progressMessage
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }

        Label {
            visible: GameDataCtrl.restartNeeded
            text: "游戏数据更新已下载，重启应用后自动生效。"
            color: palette.highlight
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
