import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components"
import "../../components/controls"
import "../../components/form"

// 基本设置：模拟器 + 启动/结束游戏
Item {
    id: root
    property var settingsCtrl
    signal modified()

    property var emulatorInstances: []
    property bool enumerationLoading: false
    property bool emulatorNotInstalled: false

    readonly property var emulatorTypeNames: ({
        mumu12: "MuMu 12 v4.x",
        mumu12v5: "MuMu 12 v5.x",
        leidian: "雷电",
        custom: "自定义",
        dmm: "DMM",
        playcover: "PlayCover (macOS)"
    })

    readonly property var validScreenshotMethods: ({
        mumu12:    [{ value: "nemu_ipc", label: "nemu_ipc" }, { value: "adb", label: "adb" }, { value: "uiautomator2", label: "uiautomator2" }],
        mumu12v5:  [{ value: "nemu_ipc", label: "nemu_ipc" }, { value: "adb", label: "adb" }, { value: "uiautomator2", label: "uiautomator2" }],
        leidian:   [{ value: "adb", label: "adb" }, { value: "uiautomator2", label: "uiautomator2" }],
        custom:    [{ value: "adb", label: "adb" }, { value: "uiautomator2", label: "uiautomator2" }],
        dmm:       [{ value: "windows_native", label: "前台挂机" }, { value: "windows_background", label: "后台挂机" }, { value: "windows", label: "前台挂机（旧）" }],
        playcover: [{ value: "macos", label: "macos" }]
    })

    readonly property var lifecycle:  settingsCtrl?.config?.profile?.backend?.lifecycle  ?? {}
    readonly property var connection: settingsCtrl?.config?.profile?.backend?.connection ?? {}
    readonly property var backend:    settingsCtrl?.config?.profile?.backend              ?? {}
    readonly property var startGame:  settingsCtrl?.config?.profile?.tasks?.start_game   ?? {}
    readonly property var endGame:    settingsCtrl?.config?.profile?.tasks?.end_game      ?? {}

    readonly property string emuType: lifecycle.type ?? "custom"
    readonly property var validMethods: validScreenshotMethods[emuType] || [{ value: "adb", label: "adb" }]

    function _commit(path, key, value) {
        var c = JSON.parse(JSON.stringify(settingsCtrl.config))
        var ref = path.split(".").reduce(function(o, k) { return o[k] }, c)
        ref[key] = value
        settingsCtrl.commitConfig(JSON.stringify(c))
        modified()
    }

    function onEmulatorTypeSelected(type) {
        var c = JSON.parse(JSON.stringify(settingsCtrl.config))
        c.profile.backend.lifecycle.type = type
        if (type === "mumu12" || type === "mumu12v5") {
            c.profile.backend.connection = { type: "auto" }
        } else if (type !== "dmm" && type !== "playcover") {
            var conn = c.profile.backend.connection || {}
            c.profile.backend.connection = { type: "tcp", ip: conn.ip || "127.0.0.1", port: conn.port || 5555 }
        }
        var valid = validScreenshotMethods[type]
        if (valid && !valid.some(function(o) { return o.value === c.profile.backend.screenshot_impl }))
            c.profile.backend.screenshot_impl = valid[0].value
        settingsCtrl.commitConfig(JSON.stringify(c))
        modified()
        root.emulatorNotInstalled = false
        root.enumerationLoading = true
        if (settingsCtrl) settingsCtrl.listEmulatorInstancesAsync(type)
    }

    Connections {
        target: settingsCtrl
        function onEmulatorInstancesReady(type, json) {
            if (type !== root.emuType) return
            root.emulatorInstances = JSON.parse(json)
            root.enumerationLoading = false
        }
        function onEmulatorNotInstalled(type) {
            if (type !== root.emuType) return
            root.emulatorNotInstalled = true
        }
    }

    FormBinder {
        id: lifecycle_b
        data: root.lifecycle
        onCommitted: function(key, value) { root._commit("profile.backend.lifecycle", key, value) }
    }
    FormBinder {
        id: backend_b
        data: root.backend
        onCommitted: function(key, value) { root._commit("profile.backend", key, value) }
    }
    FormBinder {
        id: startGame_b
        data: root.startGame
        onCommitted: function(key, value) { root._commit("profile.tasks.start_game", key, value) }
    }
    FormBinder {
        id: endGame_b
        data: root.endGame
        onCommitted: function(key, value) { root._commit("profile.tasks.end_game", key, value) }
    }

    // 模拟器实例选项（MuMu / 雷电复用）
    readonly property var instanceOptions: {
        var opts = root.emulatorInstances.map(function(e) {
            return { label: "[" + e.id + "] " + e.name, value: e.id }
        })
        return [{ label: "(请选择实例)", value: "" }].concat(opts)
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

    ColumnLayout {
        width: parent.width
        anchors.margins: 16
        spacing: 12

        // ── 设备 ────────────────────────────────────────
        GroupBox {
            title: "设备"
            Layout.fillWidth: true

            ColumnLayout {
                width: parent.width
                spacing: 8

                FormSegmentedButton {
                    label: "模拟器类型"
                    options: [
                        { label: "MuMu 12 v4.x",    value: "mumu12" },
                        { label: "MuMu 12 v5.x",    value: "mumu12v5" },
                        { label: "雷电",              value: "leidian" },
                        { label: "自定义",            value: "custom" },
                        { label: "DMM",               value: "dmm" },
                        { label: "PlayCover (macOS)", value: "playcover" }
                    ]
                    value: root.emuType
                    onUserSelected: function(v) { root.onEmulatorTypeSelected(v) }
                }

                FormNotice {
                    Layout.fillWidth: true
                    visible: root.emulatorNotInstalled
                    style: "error"
                    content: "模拟器「" + (root.emulatorTypeNames[root.emuType] ?? root.emuType) + "」未安装。如果这是 bug，请向开发者反馈。"
                }

                // MuMu12 / MuMu12v5 专属
                Loader {
                    active: (root.emuType === "mumu12" || root.emuType === "mumu12v5") && !root.emulatorNotInstalled
                    Layout.fillWidth: true
                    Layout.preferredHeight: item ? item.implicitHeight : 0
                    sourceComponent: Component {
                        ColumnLayout {
                            width: parent.width
                            spacing: 8
                            FormInstancePicker {
                                label: "选择多开实例"
                                options: root.instanceOptions
                                loading: root.enumerationLoading
                                binder: lifecycle_b
                                field: "instance_id"
                                onRefreshTriggered: {
                                    root.enumerationLoading = true
                                    settingsCtrl.listEmulatorInstancesAsync(root.emuType)
                                }
                            }
                            FormCheckBox {
                                binder: lifecycle_b
                                field: "mumu_background_mode"
                                label: "MuMu12 模拟器后台保活模式"
                            }
                            FormCheckBox {
                                binder: lifecycle_b
                                field: "check_and_start"
                                label: "自动启动模拟器"
                            }
                        }
                    }
                }

                // 雷电专属
                Loader {
                    active: root.emuType === "leidian" && !root.emulatorNotInstalled
                    Layout.fillWidth: true
                    Layout.preferredHeight: item ? item.implicitHeight : 0
                    sourceComponent: Component {
                        ColumnLayout {
                            width: parent.width
                            spacing: 8
                            FormInstancePicker {
                                label: "选择多开实例"
                                options: root.instanceOptions
                                loading: root.enumerationLoading
                                binder: lifecycle_b
                                field: "instance_id"
                                onRefreshTriggered: {
                                    root.enumerationLoading = true
                                    settingsCtrl.listEmulatorInstancesAsync(root.emuType)
                                }
                            }
                            FormTextField {
                                binder: lifecycle_b
                                field: "adb_emulator_name"
                                label: "ADB 模拟器名称（雷电专用）"
                            }
                            FormCheckBox {
                                binder: lifecycle_b
                                field: "check_and_start"
                                label: "自动启动模拟器"
                            }
                        }
                    }
                }

                // DMM / 自定义专属
                Loader {
                    active: root.emuType === "dmm" || root.emuType === "custom"
                    Layout.fillWidth: true
                    Layout.preferredHeight: item ? item.implicitHeight : 0
                    sourceComponent: Component {
                        ColumnLayout {
                            width: parent.width
                            spacing: 8
                            FormCheckBox {
                                binder: lifecycle_b
                                field: "check_and_start"
                                label: "自动启动"
                            }
                            FormTextField {
                                visible: root.lifecycle.check_and_start ?? false
                                label: "模拟器 exe 文件路径"
                                binder: lifecycle_b
                                field: "emulator_path"
                            }
                            FormTextField {
                                visible: root.lifecycle.check_and_start ?? false
                                label: "模拟器启动参数"
                                binder: lifecycle_b
                                field: "emulator_args"
                            }
                            FormCheckBox {
                                visible: root.emuType === "dmm"
                                label: "绕过 DMM 启动器"
                                binder: startGame_b
                                field: "dmm_bypass"
                            }
                            FormTextField {
                                visible: root.emuType === "dmm"
                                label: "DMM 版游戏路径 (可选)"
                                placeholder: "如：F:\\Games\\gakumas\\gakumas.exe。留空自动识别。"
                                binder: startGame_b
                                field: "dmm_game_path"
                            }
                        }
                    }
                }
            }
        }

        // ── 连接 ────────────────────────────────────────
        GroupBox {
            title: "连接"
            Layout.fillWidth: true
            visible: root.emuType === "custom" && !root.emulatorNotInstalled

            ColumnLayout {
                width: parent.width
                spacing: 8

                FormTextField {
                    label: "ADB IP 地址"
                    value: root.connection.ip ?? "127.0.0.1"
                    onUserEdited: function(v) { root._commit("profile.backend.connection", "ip", v) }
                }
                FormTextField {
                    label: "ADB 端口"
                    value: (root.connection.port ?? 5555).toString()
                    onUserEdited: function(v) { root._commit("profile.backend.connection", "port", parseInt(v, 10) || 5555) }
                }
            }
        }

        // ── 控制 ────────────────────────────────────────
        GroupBox {
            title: "控制"
            Layout.fillWidth: true
            visible: !root.emulatorNotInstalled

            ColumnLayout {
                width: parent.width
                spacing: 8

                FormSegmentedButton {
                    label: "截图方法"
                    help: "<b>截图方法说明</b><br>"
                        + "<b>adb</b> — 模拟器通用<br>"
                        + "<b>uiautomator2</b> — 模拟器通用<br>"
                        + "<b>nemu_ipc</b> — MuMu 模拟器专属（推荐）<br>"
                        + "<b>windows_native</b> — DMM 版前台挂机<br>"
                        + "<b>windows_background</b> — DMM 版后台挂机（实验性）<br>"
                        + "<b>windows</b> — DMM 版前台挂机（旧，即将移除）<br>"
                        + "<b>macos</b> — macOS 原生窗口控制"
                    options: root.validMethods
                    binder: backend_b
                    field: "screenshot_impl"
                }

                FormNotice {
                    Layout.fillWidth: true
                    visible: (root.backend.screenshot_impl ?? "") === "windows"
                    style: "warning"
                    title: "截图方法已废弃"
                    content: "「windows」控制方法已废弃，将在后续版本中移除。建议使用新的「windows_native」控制方法。"
                }
                FormNotice {
                    Layout.fillWidth: true
                    visible: (root.emuType === "mumu12" || root.emuType === "mumu12v5") && (root.backend.screenshot_impl ?? "") !== "nemu_ipc"
                    style: "tip"
                    title: "推荐配置"
                    content: "MuMu 模拟器推荐使用 nemu_ipc 截图方式，性能更佳且更稳定"
                }

                FormTextField {
                    label: "最小截图间隔（秒）"
                    value: {
                        var val = root.backend.target_screenshot_interval
                        return val != null ? Number(val).toFixed(1) : "0.5"
                    }
                    onUserEdited: function(v) {
                        var n = parseFloat(v)
                        if (!isNaN(n) && n >= 0)
                            root._commit("profile.backend", "target_screenshot_interval", n)
                    }
                }

                FormSpinBox {
                    visible: (root.backend.screenshot_impl ?? "") === "windows_background"
                    label: "后台挂机时光标最大速度（像素/秒）"
                    help: "使用 DMM 版后台挂机功能时，在点击前会尝试等待光标静止，以避免发生点击偏移。"
                        + "<br>此项规定了速度小于多少时认为光标静止，单位为像素/秒。"
                        + "<br><br><b>-1</b> 表示使用内置默认值，<b>0</b> 表示禁用该功能。"
                        + "<br>值越大，等待时间越短，脚本响应越快，但点击偏移风险上升。"
                        + "<br>值越小，等待时间越长，脚本响应越慢，但稳定性更好。"
                    labelWidth: 140
                    from: -1; to: 10000
                    binder: lifecycle_b
                    field: "cursor_wait_speed"
                }

                Button {
                    visible: root.emuType === "dmm"
                    text: "重置游戏窗口位置"
                    onClicked: if (settingsCtrl) settingsCtrl.resetGameWindow()
                }
            }
        }

        // ── 启动游戏 ────────────────────────────────────
        GroupBox {
            title: "启动游戏"
            Layout.fillWidth: true

            ColumnLayout {
                width: parent.width
                spacing: 8

                FormCheckBox {
                    binder: startGame_b
                    field: "enabled"
                    label: "启用自动启动游戏"
                }
                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    visible: root.startGame.enabled ?? false

                    FormCheckBox {
                        binder: startGame_b
                        field: "disable_gakumas_localify"
                        label: "自动禁用 Gakumas Localify 汉化"
                        enabled: root.emuType === "dmm"
                        font.strikeout: !enabled
                    }
                    FormCheckBox {
                        binder: startGame_b
                        field: "start_through_kuyo"
                        label: "通过Kuyo来启动游戏"
                        enabled: root.emuType === "mumu12" || root.emuType === "mumu12v5" || root.emuType === "leidian" || root.emuType === "custom"
                        font.strikeout: !enabled
                    }
                }
            }
        }

        // ── 结束游戏 ────────────────────────────────────
        GroupBox {
            title: "结束游戏"
            Layout.fillWidth: true

            ColumnLayout {
                width: parent.width
                spacing: 8

                Label {
                    text: "注：执行单个任务不会触发下面这些，只有主页的启动按钮才会触发"
                    color: palette.placeholderText
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                FormCheckBox {
                    binder: endGame_b
                    field: "exit_kaa"
                    label: "退出 kaa"
                }
                FormCheckBox {
                    binder: endGame_b
                    field: "kill_game"
                    label: "关闭游戏"
                }
                FormCheckBox {
                    binder: endGame_b
                    field: "kill_dmm"
                    label: "关闭 DMMGamePlayer"
                }
                FormCheckBox {
                    binder: endGame_b
                    field: "kill_emulator"
                    label: "关闭模拟器"
                }
                FormCheckBox {
                    binder: endGame_b
                    field: "shutdown"
                    label: "关闭系统"
                }
                FormCheckBox {
                    binder: endGame_b
                    field: "hibernate"
                    label: "休眠系统"
                }
                FormCheckBox {
                    binder: endGame_b
                    field: "restore_gakumas_localify"
                    label: "恢复 Gakumas Localify 汉化状态"
                    enabled: root.emuType === "dmm"
                    font.strikeout: !enabled
                }
            }
        }
    }
    } // ScrollView
}

