.pragma library

// 沿父链查找最近的 FormSection._formBinder，供各 form 组件复用。
function effectiveBinder(binder, startParent) {
    if (binder) return binder
    var p = startParent
    while (p) {
        if (p._formBinder) return p._formBinder
        p = p.parent
    }
    return null
}
