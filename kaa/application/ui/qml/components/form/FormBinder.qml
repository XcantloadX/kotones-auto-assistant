import QtQuick

// 表单数据绑定器：连接数据源和表单字段，消除重复的 read/write 样板。
// 用法：
//   FormBinder { id: b; data: someObj; onCommitted: someObj[key] = value }
//   FormCheckBox { binder: b; field: "enabled"; label: "..." }
QtObject {
    // 指向配置子树（只读，外部响应式更新）
    property var data: null

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

    // 写入字段：先触发 committed（onCommitted 完成 mutation），再递增 _revision
    function set(key, val) {
        committed(key, val)
        _revision++
    }
}
