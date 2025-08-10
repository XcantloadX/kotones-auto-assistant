import React, { useMemo } from "react";
import { Button, Form } from "react-bootstrap";
import { useRunStore } from "../../stores/runStore";

export default function RunControls() {
  const { runButton, pauseButton, endAction, toggleRun, togglePause, saveEndAction, loading } = useRunStore();

  const options = useMemo(() => [
    { label: "什么都不做", value: "DO_NOTHING" },
    { label: "关机", value: "SHUTDOWN" },
    { label: "休眠", value: "HIBERNATE" },
  ] as const, []);

  return (
    <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
      <Button className="px-4" disabled={!runButton.interactive || loading} onClick={toggleRun}>
        <i className="bi bi-play-fill me-1" />
        <span>{runButton.text}</span>
      </Button>
      <Button variant="outline-secondary" disabled={!pauseButton.interactive || loading} onClick={togglePause}>
        <i className="bi bi-pause-fill me-1" />
        <span>{pauseButton.text}</span>
      </Button>
      <div className="ms-auto small text-secondary">完成后：</div>
      <div style={{ minWidth: 220 }}>
        <Form.Select
          size="sm"
          value={endAction}
          onChange={(e) => saveEndAction(e.target.value as any)}
        >
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