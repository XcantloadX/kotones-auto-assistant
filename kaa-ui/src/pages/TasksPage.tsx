import { useEffect } from 'react';
import { Button, Alert } from 'react-bootstrap';
import { useTaskStore } from '../stores/useTaskStore';
import { useToast } from '../lib/toast';
import Breadcrumb from '../components/Breadcrumb';

export default function TasksPage() {
  const { tasks, currentTask, loading, error, fetchTasks, startTask, stopTask } = useTaskStore();
  const toast = useToast();

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error, toast]);

  return (
    <div>
      <Breadcrumb items={[{ text: '任务' }]} />

      {currentTask && currentTask.running && (
        <Alert variant="info">
          <Alert.Heading>当前运行任务</Alert.Heading>
          <p><strong>{currentTask.name}</strong></p>
          {currentTask.message && <p className="mb-0">{currentTask.message}</p>}
          <hr />
          <div className="d-flex justify-content-end">
            <Button variant="outline-danger" size="sm" onClick={stopTask} disabled={loading}>
              停止任务
            </Button>
          </div>
        </Alert>
      )}

      <div className="mb-4">
        {tasks.length === 0 && (
          <div className="text-center text-muted p-4">
            {loading ? '加载中...' : '暂无任务'}
          </div>
        )}

        {tasks.map((task) => (
          <div key={task.name} className="d-flex align-items-center p-3 border rounded mb-2 bg-light">
            <Button
              variant="primary"
              size="sm"
              className="me-3"
              onClick={() => startTask(task.name)}
              disabled={!task.enabled || loading || (currentTask?.running ?? false)}
              title="启动任务"
            >
              ▶
            </Button>
            <div className="flex-grow-1">
              <h6 className="mb-1"><strong>{task.display_name || task.name}</strong></h6>
              <p className="mb-0 text-muted small">{task.description || '-'}</p>
            </div>
            <span className={`badge ${task.enabled ? 'bg-success' : 'bg-secondary'}`}>
              {task.enabled ? '已启用' : '已禁用'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

