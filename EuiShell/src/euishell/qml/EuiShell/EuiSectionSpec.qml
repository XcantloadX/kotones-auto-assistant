import QtQml

// 设置页 / 偏好页 section 规格：声明顺序即渲染顺序。
QtObject {
    property string title
    // section Tab 标题。

    property Component source
    // section 组件，由框架在挂载页内实例化。
}
