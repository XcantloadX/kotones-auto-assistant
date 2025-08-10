import { useEffect, useMemo, useState } from "react";
import { Button, ButtonGroup, Image, ToggleButton } from "react-bootstrap";

export default function ScreenPage() {
  const [ts, setTs] = useState<number>(Date.now());
  const [last, setLast] = useState<string>("无数据");
  const [size, setSize] = useState<"thumb" | "full">("thumb");
  const [mode, setMode] = useState<"current" | "last">("current");
  const reload = () => setTs(Date.now());
  useEffect(() => {
    setLast(new Date(ts).toLocaleString());
  }, [ts]);
  const url = useMemo(() => `/api/v1/screen/${mode}?size=${size}&_=${ts}`, [mode, size, ts]);
  return (
    <div className="card">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <div className="fw-bold">当前设备画面</div>
          <div className="d-flex align-items-center gap-2">
            <ButtonGroup size="sm">
              <ToggleButton id="mode-current" type="radio" variant="outline-secondary" name="mode" value="current" checked={mode === "current"} onChange={() => setMode("current")}>current</ToggleButton>
              <ToggleButton id="mode-last" type="radio" variant="outline-secondary" name="mode" value="last" checked={mode === "last"} onChange={() => setMode("last")}>last</ToggleButton>
            </ButtonGroup>
            <ButtonGroup size="sm">
              <ToggleButton id="size-thumb" type="radio" variant="outline-secondary" name="size" value="thumb" checked={size === "thumb"} onChange={() => setSize("thumb")}>thumb</ToggleButton>
              <ToggleButton id="size-full" type="radio" variant="outline-secondary" name="size" value="full" checked={size === "full"} onChange={() => setSize("full")}>full</ToggleButton>
            </ButtonGroup>
            <Button size="sm" onClick={reload}>
              <i className="bi bi-arrow-clockwise me-1" />刷新
            </Button>
          </div>
        </div>
        <div className="row g-3">
          <div className="col-12 col-md-4 order-2 order-md-1">
            <div className="small text-secondary">上次更新时间：{last}</div>
          </div>
          <div className="col-12 col-md-8 order-1 order-md-2">
            <Image src={url} thumbnail />
          </div>
        </div>
      </div>
    </div>
  );
} 