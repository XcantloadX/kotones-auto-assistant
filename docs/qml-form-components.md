# QML 表单原语组件

## 目标

建立一套薄的 QML 表单原语，消灭 Section 内的布局重复和 options 映射重复。组件只管呈现，不知道 cfg。

---

## 组件列表

新建目录：`kaa/application/ui/qml/components/form/`

### `FormCheckBox.qml`

```qml
RowLayout {
    id: root
    property string label: ""
    property string help: ""
    property bool value: false
    signal valueChanged(bool v)

    CheckBox {
        text: root.label
        checked: root.value
        onToggled: root.valueChanged(checked)   // onToggled 只在用户点击时触发，不产生绑定循环
    }
    // HelpTip { visible: root.help.length > 0; text: root.help }
}
```

### `FormComboBox.qml`

```qml
RowLayout {
    id: root
    property string label: ""
    property string help: ""
    property var options: []    // 支持 ["str", ...] 或 [{label, value}, ...]
    property var value: null
    signal valueChanged(var v)

    Label { text: root.label; Layout.preferredWidth: 120 }

    ComboBox {
        Layout.fillWidth: true
        model: root.options.map(o => typeof o === "object" ? o.label : String(o))
        currentIndex: {
            for (var i = 0; i < root.options.length; i++) {
                var v = typeof root.options[i] === "object" ? root.options[i].value : root.options[i]
                if (v === root.value) return i
            }
            return -1
        }
        onActivated: {
            var o = root.options[currentIndex]
            root.valueChanged(typeof o === "object" ? o.value : o)
        }
    }
}
```

### `FormTextField.qml`

```qml
RowLayout {
    id: root
    property string label: ""
    property string value: ""
    property string placeholder: ""
    signal valueChanged(string v)

    Label { text: root.label; Layout.preferredWidth: 120 }
    TextField {
        Layout.fillWidth: true
        text: root.value
        placeholderText: root.placeholder
        onTextEdited: root.valueChanged(text)
    }
}
```

### `FormSpinBox.qml`

```qml
RowLayout {
    id: root
    property string label: ""
    property int from: 0
    property int to: 100
    property var value: 0
    property var read:  function(v) { return v ?? 0 }   // 存储值 → 显示值（可覆盖，处理 null 等特殊情况）
    property var write: function(v) { return v }         // 显示值 → 存储值（可覆盖）
    signal valueChanged(var v)

    Label { text: root.label; Layout.preferredWidth: 120 }
    SpinBox {
        from: root.from; to: root.to
        value: root.read(root.value)
        onValueModified: root.valueChanged(root.write(value))
    }
}
```

`read`/`write` 用于处理存储值与显示值不同类型的情况，例如：

```qml
FormSpinBox {
    label: "最小截图间隔(秒)"
    from: 0; to: 10000
    value: screenshotInterval
    read:  v => v ?? 0           // null → 0 给 SpinBox 看
    write: v => v === 0 ? null : v  // 0 → null 存回 cfg
    onValueChanged: v => screenshotInterval = v
}
```

### `FormNotice.qml`

替代 Gradio 的 `Alert` 组件。

```qml
// style ∈ {"info", "tip", "warning", "error"}
Rectangle {
    id: root
    property string style: "info"
    property string title: ""
    property string content: ""

    readonly property var _colors: ({
        info:    { bg: "#E3F2FD", border: "#BBDEFB" },
        tip:     { bg: "#E8F5E9", border: "#C8E6C9" },
        warning: { bg: "#FFF3E0", border: "#FFE0B2" },
        error:   { bg: "#FFEBEE", border: "#FFCDD2" }
    })

    color: (_colors[style] ?? _colors.info).bg
    border.color: (_colors[style] ?? _colors.info).border
    border.width: 1
    radius: 4
    implicitHeight: layout.implicitHeight + 24

    ColumnLayout {
        id: layout
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
        spacing: 4
        Label {
            text: root.title
            font.weight: Font.DemiBold
            visible: root.title.length > 0
            Layout.fillWidth: true
        }
        Label {
            text: root.content
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
```

---

## Section 内的使用约定

**两层分离：**

1. **顶部**：Section 声明本地属性，负责 cfg 读取和写回，`modified()` 只在此层调用
2. **字段层**：只引用本地属性，不出现 cfg 路径，不出现 `modified()`

```qml
// DailySection.qml（示例）
Item {
    id: root
    property var cfg
    signal modified()

    // ── 顶部：cfg 路径只在此出现 ──────────────────────────────
    property bool moneyEnabled:     cfg?.profile?.tasks?.purchase?.money_enabled      ?? false
    property bool apEnabled:        cfg?.profile?.tasks?.purchase?.ap_enabled         ?? false
    property int  miniLiveDuration: cfg?.profile?.tasks?.assignment?.mini_live_duration ?? 4

    onMoneyEnabledChanged:     { cfg.profile.tasks.purchase.money_enabled = moneyEnabled; modified() }
    onApEnabledChanged:        { cfg.profile.tasks.purchase.ap_enabled = apEnabled; modified() }
    onMiniLiveDurationChanged: { cfg.profile.tasks.assignment.mini_live_duration = miniLiveDuration; modified() }

    // ── 字段层：无 cfg 路径，无 modified() ────────────────────
    GroupBox {
        title: "商店购买"

        ColumnLayout {
            FormCheckBox {
                label: "购买金币物品"
                value: root.moneyEnabled
                onValueChanged: v => root.moneyEnabled = v
            }
            FormCheckBox {
                label: "购买 AP 物品"
                value: root.apEnabled
                onValueChanged: v => root.apEnabled = v
            }
        }
    }

    GroupBox {
        title: "工作"

        FormComboBox {
            label: "MiniLive 时长"
            options: [{label: "4小时", value: 4}, {label: "6小时", value: 6}, {label: "12小时", value: 12}]
            value: root.miniLiveDuration
            onValueChanged: v => root.miniLiveDuration = v
        }
    }
}
```

---

## 例外：多字段联动

联动逻辑（一个字段变更触发多个字段写入）不适合本地属性模式——因为多个属性的 `onXxxChanged` 会各自独立触发，无法原子地更新多个字段。直接保持命令式写法，集中在 Section 顶部的函数里：

```qml
// EmulatorSection.qml
function onEmulatorTypeSelected(type) {
    cfg.profile.backend.lifecycle.type = type
    var valid = validScreenshotMethods[type]
    if (!valid.includes(cfg.profile.backend.screenshot_impl))
        cfg.profile.backend.screenshot_impl = valid[0]
    modified()
    settingsCtrl.listEmulatorInstancesAsync(type)
}
```

---

## 文件清单

| 文件 | 说明 |
|---|---|
| `qml/components/form/FormCheckBox.qml` | label + CheckBox |
| `qml/components/form/FormComboBox.qml` | label + ComboBox，归一化 options |
| `qml/components/form/FormTextField.qml` | label + TextField |
| `qml/components/form/FormSpinBox.qml` | label + SpinBox，可选 read/write 变换 |
| `qml/components/form/FormNotice.qml` | info/tip/warning/error 样式提示块 |
