import { useEffect } from "react";
import { Alert } from "react-bootstrap";
import { useRunStore } from "../stores/runStore";
import TaskCard from "../components/status/TaskCard";

export default function TasksPage() {
  const { tasks, isRunning, toggleRun, loading, refresh } = useRunStore();

  useEffect(() => {
    if (!tasks.length) {
      refresh();
    }
  }, [tasks.length, refresh]);

  return (
    <div className="row g-3">
      <div className="col-12">
        {isRunning && (
          <Alert variant="warning" className="mb-3">
            当前正在运行其他任务。若需要执行新任务，需要停止原有任务的执行
          </Alert>
        )}

        <div className="row g-3">
          {tasks.map((task) => (
            <div key={task.name} className="col-12 col-md-6 col-lg-4">
              <TaskCard task={task} onRun={toggleRun} disabled={isRunning || loading} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
} 