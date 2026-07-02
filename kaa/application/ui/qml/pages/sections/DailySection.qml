import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components/controls"
import "../../components/form"

// 日常设置：商店 / 工作 / 竞赛 / 奖励
//
// 金币/AP 物品枚举值参考 kaa/config/const.py：
//   DailyMoneyShopItems.value → int
//   APShopItems.value         → int
Item {
    id: root
    property var settingsCtrl
    signal modified()

    property var moneyItemModel: []
    property var apItemModel: []
    property var noteModel: []

    readonly property var _purchase:   settingsCtrl?.config?.profile?.tasks?.purchase   ?? {}
    readonly property var _assignment: settingsCtrl?.config?.profile?.tasks?.assignment ?? {}
    readonly property var _contest:    settingsCtrl?.config?.profile?.tasks?.contest    ?? {}
    readonly property var _tasks:      settingsCtrl?.config?.profile?.tasks             ?? {}

    function loadStaticData() {
        if (!settingsCtrl) return
        moneyItemModel = JSON.parse(settingsCtrl.moneyShopItemsJson())
        apItemModel    = JSON.parse(settingsCtrl.apShopItemsJson())
        noteModel      = JSON.parse(settingsCtrl.noteItemsJson())
    }

    function _commit(path, key, value) {
        var c = JSON.parse(JSON.stringify(settingsCtrl.config))
        var ref = path.split(".").reduce(function(o, k) { return o[k] }, c)
        ref[key] = value
        settingsCtrl.commitConfig(JSON.stringify(c))
        modified()
    }

    Component.onCompleted: loadStaticData()

    FormBinder {
        id: purchase
        data: root._purchase
        onCommitted: function(key, value) { root._commit("profile.tasks.purchase", key, value) }
    }
    FormBinder {
        id: assignment
        data: root._assignment
        onCommitted: function(key, value) { root._commit("profile.tasks.assignment", key, value) }
    }
    FormBinder {
        id: contest
        data: root._contest
        onCommitted: function(key, value) { root._commit("profile.tasks.contest", key, value) }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            anchors.margins: 16
            spacing: 12

            // ── 商店购买 ──────────────────────────────────
            FormGroupBox {
                title: "商店购买"
                binder: purchase

                FormCheckBox {
                    field: "enabled"
                    label: "启用商店购买"
                }

                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    visible: root._purchase.enabled ?? false

                    FormCheckBox {
                        field: "money_enabled"
                        label: "启用金币购买"
                    }

                    ColumnLayout {
                        width: parent.width
                        spacing: 8
                        Layout.leftMargin: 24
                        visible: root._purchase.money_enabled ?? false

                        MultiSelect {
                            Layout.fillWidth: true
                            label: "金币商店购买物品"
                            model: root.moneyItemModel
                            selectedValues: root._purchase.money_items ?? []
                            onSelectionChanged: root._commit("profile.tasks.purchase", "money_items", selectedValues)
                        }

                        FormCheckBox {
                            field: "money_refresh"
                            label: "每日一次免费刷新金币商店"
                        }
                    }

                    FormCheckBox {
                        field: "ap_enabled"
                        label: "启用AP购买"
                    }

                    ColumnLayout {
                        width: parent.width
                        spacing: 8
                        Layout.leftMargin: 24
                        visible: root._purchase.ap_enabled ?? false

                        MultiSelect {
                            Layout.fillWidth: true
                            label: "AP商店购买物品"
                            model: root.apItemModel
                            selectedValues: root._purchase.ap_items ?? []
                            onSelectionChanged: root._commit("profile.tasks.purchase", "ap_items", selectedValues)
                        }
                    }

                    FormCheckBox {
                        field: "weekly_enabled"
                        label: "启用每周免费礼包购买"
                    }
                }
            }

            // ── 工作 ──────────────────────────────────────
            FormGroupBox {
                title: "工作"
                binder: assignment

                FormCheckBox {
                    field: "enabled"
                    label: "启用工作"
                }

                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    visible: root._assignment.enabled ?? false

                    FormCheckBox {
                        field: "mini_live_reassign_enabled"
                        label: "启用重新分配 MiniLive"
                    }
                    FormSegmentedButton {
                        field: "mini_live_duration"
                        label: "MiniLive 工作时长"
                        options: [
                            { label: "4小时", value: 4 },
                            { label: "6小时", value: 6 },
                            { label: "12小时", value: 12 }
                        ]
                    }
                    FormCheckBox {
                        field: "online_live_reassign_enabled"
                        label: "启用重新分配 OnlineLive"
                    }
                    FormSegmentedButton {
                        field: "online_live_duration"
                        label: "OnlineLive 工作时长"
                        options: [
                            { label: "4小时", value: 4 },
                            { label: "6小时", value: 6 },
                            { label: "12小时", value: 12 }
                        ]
                    }
                }
            }

            // ── 竞赛 ──────────────────────────────────────
            FormGroupBox {
                title: "竞赛"
                binder: contest

                FormCheckBox {
                    field: "enabled"
                    label: "启用竞赛"
                }

                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    visible: root._contest.enabled ?? false

                    FormSegmentedButton {
                        field: "select_which_contestant"
                        label: "选择第几个挑战者"
                        options: [
                            { label: "1号", value: 1 },
                            { label: "2号", value: 2 },
                            { label: "3号", value: 3 }
                        ]
                    }
                    FormComboBox {
                        field: "when_no_set"
                        label: "竞赛队伍未编成时"
                        options: [
                            { label: "通知我并跳过竞赛", value: "remind" },
                            { label: "提醒我并等待手动编成", value: "wait" },
                            { label: "使用自动编成并提醒我", value: "auto_set" },
                            { label: "使用自动编成", value: "auto_set_silent" }
                        ]
                    }
                }
            }

            // ── 奖励 ──────────────────────────────────────
            // 各字段指向 _tasks 下不同的子路径，不适合单一 binder，保留显式写法
            GroupBox {
                title: "奖励"
                Layout.fillWidth: true
                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    FormCheckBox {
                        label: "领取任务奖励"
                        value: root._tasks.mission_reward?.enabled ?? false
                        onUserToggled: function(checked) { root._commit("profile.tasks.mission_reward", "enabled", checked) }
                    }
                    FormCheckBox {
                        label: "领取社团奖励"
                        value: root._tasks.club_reward?.enabled ?? false
                        onUserToggled: function(checked) { root._commit("profile.tasks.club_reward", "enabled", checked) }
                    }
                    FormComboBox {
                        Layout.leftMargin: 24
                        visible: root._tasks.club_reward?.enabled ?? false
                        label: "社团奖励笔记选择"
                        options: root.noteModel.map(function(note) { return { label: note.text, value: note.value } })
                        value: root._tasks.club_reward?.selected_note ?? 3
                        onUserSelected: function(v) { root._commit("profile.tasks.club_reward", "selected_note", v) }
                    }
                    FormCheckBox {
                        label: "收取礼物"
                        value: root._tasks.presents?.enabled ?? false
                        onUserToggled: function(checked) { root._commit("profile.tasks.presents", "enabled", checked) }
                    }
                    FormCheckBox {
                        label: "收取活动费"
                        value: root._tasks.activity_funds?.enabled ?? false
                        onUserToggled: function(checked) { root._commit("profile.tasks.activity_funds", "enabled", checked) }
                    }
                    FormCheckBox {
                        label: "扭蛋机"
                        value: root._tasks.capsule_toys?.enabled ?? false
                        onUserToggled: function(checked) { root._commit("profile.tasks.capsule_toys", "enabled", checked) }
                    }
                    FormCheckBox {
                        label: "升级支援卡"
                        value: root._tasks.upgrade_support_card?.enabled ?? false
                        onUserToggled: function(checked) { root._commit("profile.tasks.upgrade_support_card", "enabled", checked) }
                    }
                }
            }
        }
    }
}
