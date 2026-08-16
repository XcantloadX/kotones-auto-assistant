import QtQuick

// 表单数据绑定器：连接数据源和表单字段，消除重复的 read/write 样板。
// 用法：
//   FormBinder { id: b; data: someObj; onCommitted: someObj[key] = value }
//   FormCheckBox { binder: b; field: "enabled"; label: "..." }
QtObject {
    // 指向配置子树（只读，外部响应式更新）
    property var data: null

    // 该 binder 数据子树对应的完整 dot path（如 "tasks.purchase"）。
    // 用于把校验 issue.field 映射回本 binder 内的字段。
    property string prefix: ""

    // 完整 dot path → {severity, message} 的校验问题映射（来自 SettingsPage）
    property var errors: ({})

    // 字段修改信号：section 监听此信号来持久化变更
    signal committed(string key, var value)

    // 每次 set() 后递增，使 get() 的调用方绑定能感知字段变化
    property int _revision: 0

    // 读取字段值，data 为 null 或字段缺失时返回 fallback
    // 注意：必须引用 _revision，使 QML 绑定引擎在任意字段写入后重新求值
    function get(key, fallback) {
        var _ = _revision
        if (data === null || data === undefined) return fallback
        var v = data[key]
        return (v !== undefined && v !== null) ? v : fallback
    }

    // 按字段名（相对本 binder）查询校验问题，无问题时返回 null
    function error(field) {
        if (!errors || !field) return null
        var full = prefix ? (prefix + "." + field) : field
        return errors[full] || null
    }

    // 写入字段：先触发 committed（onCommitted 完成 mutation），再递增 _revision
    function set(key, val) {
        committed(key, val)
        _revision++
    }
}
