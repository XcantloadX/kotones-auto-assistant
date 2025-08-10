import { Button } from "react-bootstrap";
import { useRunStore } from "../stores/runStore";
import TaskTable from "../components/status/TaskTable";

export default function TasksPage() {
  const { refresh, loading } = useRunStore();
  return (
    <div className="row g-3">
      <div className="col-12">
        <div className="d-flex justify-content-end mb-2">
          <Button size="sm" onClick={refresh} disabled={loading}>
            刷新
          </Button>
        </div>
        <TaskTable />
      </div>
    </div>
  );
} 