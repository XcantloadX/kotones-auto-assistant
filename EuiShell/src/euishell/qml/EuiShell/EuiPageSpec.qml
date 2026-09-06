import QtQml

// Tab 内自定义页面规格：声明顺序即导航顺序（位于设置页之后、日志页之前）。
QtObject {
    property string title
    // 侧边导航标题。

    property Component source
    // 页面组件，由框架在每 Tab 内实例化一份。
}
