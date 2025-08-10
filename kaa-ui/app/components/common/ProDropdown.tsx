import React, { useEffect, useMemo, useRef, useState } from "react";

export type ProOption<T = string | number> = {
  /** 显示文本 */
  label: string;
  /** 选项值（string 或 number） */
  value: T;
  /** 可选：附加元数据，便于自定义渲染 */
  meta?: any;
};

export type ProDropdownProps<T = string | number> = {
  /** 是否多选；多选时输入框内以标签形式展示（默认 false） */
  multiple?: boolean;
  /** 当前值；单选为 T 或 null，多选为 T[] */
  value?: T | T[] | null;
  /** 值变更回调 */
  onChange?: (value: T | T[] | null) => void;
  /** 选项 */
  options?: ProOption<T>[];
  /** 是否启用搜索过滤（默认启用） */
  search?: boolean;
  /** 自定义搜索函数（入参：option, query），返回 true 表示命中 */
  searchFn?: (option: ProOption<T>, query: string) => boolean;
  /** 占位提示 */
  placeholder?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 自定义下拉项渲染 */
  renderItem?: (option: ProOption<T>, selected: boolean) => React.ReactNode;
  /** 自定义类名 */
  className?: string;
  /** 多选标签最多展示数量；不设置时不折叠 */
  maxTagCount?: number;
};

export default function ProDropdown<T = string | number>(props: ProDropdownProps<T>) {
  const {
    multiple = false,
    value,
    onChange,
    options,
    search = true,
    searchFn,
    placeholder,
    disabled,
    renderItem,
    className,
    maxTagCount,
  } = props;

  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // 点击外部关闭
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!containerRef.current) return;
      if (containerRef.current.contains(e.target as Node)) return;
      setIsOpen(false);
      // 关闭时清空搜索查询
      if (!multiple) {
        setQuery("");
      }
    };
    document.addEventListener("click", handler, true);
    return () => document.removeEventListener("click", handler, true);
  }, [multiple]);

  const selectedValues: T[] = useMemo(() => {
    if (multiple) return Array.isArray(value) ? (value as T[]) : value != null ? [value as T] : [];
    return value != null ? [value as T] : [];
  }, [value, multiple]);

  const isSelected = (v: T) => selectedValues.some((x) => x === v);

  const allOptions: ProOption<T>[] = useMemo(() => options ?? [], [options]);

  const filteredOptions = useMemo(() => {
    const data = allOptions;
    if (!search || !query) return data;
    const q = query.toLowerCase();
    const fn = searchFn ?? ((o: ProOption<T>, qq: string) => o.label.toLowerCase().includes(qq));
    return data.filter((o) => fn(o, q));
  }, [allOptions, search, query, searchFn]);

  // 将选中值映射为选中项（用于标签与单选显示）；若未找到则回退显示 value 文本
  const selectedOptions: ProOption<T>[] = useMemo(() => {
    const map = new Map<any, ProOption<T>>();
    for (const o of allOptions) map.set(o.value as any, o);
    return selectedValues.map((v) => map.get(v as any) ?? { label: String(v), value: v });
  }, [selectedValues, allOptions]);

  const emitChange = (vals: T[] | null) => {
    if (!onChange) return;
    if (multiple) onChange(vals ?? [] as unknown as T[]);
    else onChange(vals && vals.length ? (vals[0] as T) : (null as any));
  };

  const toggleValue = (v: T) => {
    if (multiple) {
      const exists = isSelected(v);
      const next = exists ? selectedValues.filter((x) => x !== v) : [...selectedValues, v];
      emitChange(next);
    } else {
      const next = isSelected(v) ? [] : [v];
      emitChange(next);
      setIsOpen(false);
      setQuery(""); // 选择后清空搜索
    }
  };

  const removeValue = (v: T) => {
    if (!multiple) return;
    const next = selectedValues.filter((x) => x !== v);
    emitChange(next);
  };

  const openMenu = () => {
    if (disabled) return;
    setIsOpen(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  // 单选时的显示文本：如果有选中项且不在搜索状态，显示选中项的标签；否则显示搜索查询
  const getDisplayText = () => {
    if (multiple) return query;
    if (isOpen || query) return query; // 打开下拉或有搜索查询时显示搜索文本
    return selectedOptions[0]?.label || ""; // 否则显示选中项的标签
  };

  // 多标签折叠；不设置 maxTagCount 时不折叠
  const limit = typeof maxTagCount === "number" ? maxTagCount : selectedOptions.length;
  const tagsToShow = multiple ? selectedOptions.slice(0, limit) : [];
  const hiddenCount = multiple ? Math.max(0, selectedOptions.length - limit) : 0;

  return (
    <div className={"position-relative " + (className ?? "")} ref={containerRef}>
      <div
        className={"form-control d-flex align-items-center flex-wrap gap-1 " + (disabled ? " disabled" : "")}
        onClick={openMenu}
        style={{ cursor: disabled ? "not-allowed" : "text", minHeight: 38 }}
      >
        {multiple && tagsToShow.map((opt) => (
          <span key={String(opt.value)} className="badge rounded-pill bg-secondary d-inline-flex align-items-center">
            <span className="me-1">{opt.label}</span>
            {!disabled && (
              <button
                type="button"
                className="ms-1 text-white text-decoration-none bg-transparent border-0"
                style={{ lineHeight: 1, padding: 0 }}
                aria-label="移除"
                onClick={(e) => { e.stopPropagation(); removeValue(opt.value); }}
              >
                ×
              </button>
            )}
          </span>
        ))}
        {multiple && hiddenCount > 0 && (
          <span className="badge rounded-pill bg-secondary">+{hiddenCount}</span>
        )}
        <input
          ref={inputRef}
          type="text"
          className="border-0 flex-grow-1"
          style={{ outline: "none", minWidth: 60 }}
          value={getDisplayText()}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={selectedOptions.length && !isOpen ? "" : (placeholder ?? "请选择")}
          disabled={disabled}
        />
      </div>

      {isOpen && (
        <div className="dropdown-menu show w-100 mt-1 p-0" style={{ maxHeight: 300, overflowY: "auto" }}>
          {!filteredOptions.length && (
            <div className="px-3 py-2 text-secondary small">无匹配项</div>
          )}
          {filteredOptions.map((opt) => {
            const selected = isSelected(opt.value);
            return (
              <button
                type="button"
                key={String(opt.value)}
                className="dropdown-item d-flex align-items-center"
                onClick={() => toggleValue(opt.value)}
              >
                <i className={`bi bi-check2 me-2 ${selected ? "text-primary" : "invisible"}`}></i>
                {renderItem ? renderItem(opt, selected) : (<span>{opt.label}</span>)}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
} 