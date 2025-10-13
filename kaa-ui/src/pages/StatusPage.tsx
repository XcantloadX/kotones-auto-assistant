import { useEffect } from 'react';
import { Card, Button, Table } from 'react-bootstrap';
import { useRunStore } from '../stores/useRunStore';
import Breadcrumb from '../components/Breadcrumb';

export default function StatusPage() {
  const { status, loading, startAll, stopAll, togglePause, fetchStatus } = useRunStore();

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);


  return (
    <div>
      <Breadcrumb items={[{ text: '运行状态' }]} />

      {/* 引擎控制 */}
      <Card className="mb-4">
        <Card.Header>
          <strong>引擎控制</strong>
        </Card.Header>
        <Card.Body>
          <div className="d-flex gap-2">
            <Button
              variant={status.running ? 'danger' : 'success'}
              onClick={status.running ? stopAll : startAll}
              disabled={loading}
            >
              {status.running ? '停止' : '启动'}
            </Button>
            <Button
              variant="warning"
              onClick={togglePause}
              disabled={!status.running || loading}
            >
              {status.paused ? '继续' : '暂停'}
            </Button>
          </div>
        </Card.Body>
      </Card>


      {/* 状态信息 */}
      <Card>
        <Card.Header>
          <strong>状态详情</strong>
        </Card.Header>
        <Card.Body>
          <Table striped bordered hover>
            <tbody>
              <tr>
                <td><strong>运行状态</strong></td>
                <td>
                  <span className={`badge ${status.running ? 'bg-success' : 'bg-secondary'}`}>
                    {status.running ? '运行中' : '已停止'}
                  </span>
                </td>
              </tr>
              <tr>
                <td><strong>暂停状态</strong></td>
                <td>
                  <span className={`badge ${status.paused ? 'bg-warning' : 'bg-secondary'}`}>
                    {status.paused ? '已暂停' : '未暂停'}
                  </span>
                </td>
              </tr>
              {status.current_task && (
                <tr>
                  <td><strong>当前任务</strong></td>
                  <td>{status.current_task}</td>
                </tr>
              )}
              {status.message && (
                <tr>
                  <td><strong>消息</strong></td>
                  <td>{status.message}</td>
                </tr>
              )}
              {status.progress && (
                <tr>
                  <td><strong>进度</strong></td>
                  <td>
                    {status.progress.current} / {status.progress.total}
                    <div className="progress mt-2">
                      <div
                        className="progress-bar"
                        role="progressbar"
                        style={{
                          width: `${(status.progress.current / status.progress.total) * 100}%`,
                        }}
                      />
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  );
}

