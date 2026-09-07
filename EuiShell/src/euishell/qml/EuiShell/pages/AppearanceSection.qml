import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components/form"

// 偏好页内置外观 section：窗口背景样式 / 色彩方案 / 主题色。
// 保存后由 ShellApp 实时应用（AppearanceController.refresh）。
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

    function _set(path, value) {
        root.prefsCtrl.setField(path, value)
    }

    FormGroupBox {
        title: "外观"
        Layout.fillWidth: true

        FormComboBox {
            label: "窗口背景样式"
            value: root._get("interface.window_style") || ""
            options: [
                { label: "自动", value: "" },
                { label: "Mica（仅 Win 11）", value: "mica" },
                { label: "模糊背景", value: "blur" },
                { label: "亚克力（Win 10 1803+）", value: "acrylic" },
                { label: "纯色背景", value: "solid" },
            ]
            onUserSelected: function(v) { root._set("interface.window_style", v) }
        }

        FormComboBox {
            label: "色彩方案"
            value: root._get("interface.color_scheme") || "auto"
            options: [
                { label: "跟随系统", value: "auto" },
                { label: "浅色", value: "light" },
                { label: "深色", value: "dark" },
            ]
            onUserSelected: function(v) { root._set("interface.color_scheme", v) }
        }

        FormComboBox {
            label: "主题色"
            value: root._get("interface.theme_color") || ""
            options: [
                { label: "跟随系统", value: "" },
                { label: "蓝色（#0078D4）", value: "#0078d4" },
                { label: "红色（#E81123）", value: "#e81123" },
                { label: "绿色（#107C10）", value: "#107c10" },
                { label: "橙色（#FF8C00）", value: "#ff8c00" },
                { label: "紫色（#5C2D91）", value: "#5c2d91" },
                { label: "青色（#00B7C3）", value: "#00b7c3" },
                { label: "靛蓝（#6B69D6）", value: "#6b69d6" },
                { label: "石墨灰（#4A5459）", value: "#4a5459" },
            ]
            onUserSelected: function(v) { root._set("interface.theme_color", v || null) }
        }
    }
}
