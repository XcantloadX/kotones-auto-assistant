import React from "react";
import { Button, Card } from "react-bootstrap";
import type { TaskRow } from "../../services/api/run";

interface TaskCardProps {
  task: TaskRow;
  onRun: () => void;
  disabled: boolean;
}

export default function TaskCard({ task, onRun, disabled }: TaskCardProps) {
  return (
    <Card className="h-100">
      <Card.Body className="d-flex justify-content-between align-items-start">
        <div>
          <h5 className="mb-2">{task.name}</h5>
          <div className="text-muted small">
            {/* 任务描述将在未来实现 */}
          </div>
        </div>
        <Button
          variant="primary"
          onClick={onRun}
          disabled={disabled}
          className="ms-3"
        >
          运行
        </Button>
      </Card.Body>
    </Card>
  );
} 