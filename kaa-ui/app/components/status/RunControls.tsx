import React, { useMemo } from "react";
import { Button, Form } from "react-bootstrap";
import { useRunStore } from "../../stores/runStore";

export default function RunControls() {
  const { endAction, toggleRun, togglePause, saveEndAction, loading, isRunning, isPaused, isStopping } = useRunStore();

  const runText = useMemo(() => (isRunning ? (isStopping ? "停止中..." : "停止") : "启动"), [isRunning, isStopping]);
  const pauseText = useMemo(() => (isPaused ? "恢复" : "暂停"), [isPaused]);

  const canRun = useMemo(() => !isStopping && !loading, [isStopping, loading]);
  const canPause = useMemo(() => !isStopping && !loading, [isStopping, loading]);

  const options = useMemo(
    () => [
      { label: "什么都不做", value: "DO_NOTHING" },
      { label: "关机", value: "SHUTDOWN" },
      { label: "休眠", value: "HIBERNATE" },
    ] as const,
    []
  );

  return (
    <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
      <Button className="px-4" disabled={!canRun} onClick={toggleRun}>
        <i className="bi bi-play-fill me-1" />
        <span>{runText}</span>
      </Button>
      <Button variant="outline-secondary" disabled={!canPause} onClick={togglePause}>
        <i className="bi bi-pause-fill me-1" />
        <span>{pauseText}</span>
      </Button>
      <div className="small text-secondary me-2">完成后：</div>
      <div style={{ minWidth: 160 }}>
        <Form.Select size="sm" value={endAction} onChange={(e) => saveEndAction(e.target.value as any)}>
          {options.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </Form.Select>
      </div>
    </div>
  );
} 