import { useEffect, useState } from 'react';
import { Card, Button, Table } from 'react-bootstrap';
import { call } from '../lib/rpc';
import { useToast } from '../lib/toast';

interface Version {
  version: string;
  release_date?: string;
  compatible: boolean;
  changelog?: string;
}

export default function UpdatesPage() {
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    fetchVersions();
  }, []);

  const fetchVersions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await call<Version[]>('updates.list_versions');
      setVersions(data);
    } catch (err: any) {
      setError(err.message);
      toast.error(err.message || '获取版本列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (version: string) => {
    if (!confirm(`确定要安装版本 ${version} 吗？安装后程序将自动退出。`)) {
      return;
    }

    try {
      setInstalling(true);
      setError(null);
      await call('updates.install', { version });
      toast.info('更新开始安装，程序即将退出...');
    } catch (err: any) {
      setError(err.message);
      toast.error(err.message || '安装失败');
      setInstalling(false);
    }
  };

  return (
    <div>
      <h2 className="mb-4">版本更新</h2>


      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <strong>可用版本</strong>
          <Button variant="primary" size="sm" onClick={fetchVersions} disabled={loading}>
            刷新
          </Button>
        </Card.Header>
        <Card.Body>
          <Table striped bordered hover>
            <thead>
              <tr>
                <th>版本</th>
                <th>发布日期</th>
                <th>兼容性</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {versions.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-muted">
                    {loading ? '加载中...' : '暂无可用版本'}
                  </td>
                </tr>
              )}
              {versions.map((version) => (
                <tr key={version.version}>
                  <td><strong>{version.version}</strong></td>
                  <td>{version.release_date || '-'}</td>
                  <td>
                    <span className={`badge ${version.compatible ? 'bg-success' : 'bg-warning'}`}>
                      {version.compatible ? '兼容' : '不兼容'}
                    </span>
                  </td>
                  <td>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleInstall(version.version)}
                      disabled={!version.compatible || loading || installing}
                    >
                      安装
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  );
}

