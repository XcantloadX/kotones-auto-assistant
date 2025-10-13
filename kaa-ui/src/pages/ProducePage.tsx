import { useEffect, useState } from 'react';
import { Card, Button, Table, Modal, Form, Alert } from 'react-bootstrap';
import { useProduceStore } from '../stores/useProduceStore';
import { useToast } from '../lib/toast';

export default function ProducePage() {
  const { configs, loading, error, fetchConfigs, createConfig, deleteConfig } = useProduceStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');
  const toast = useToast();

  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  const handleCreate = async () => {
    try {
      await createConfig(newConfigName);
      setShowCreateModal(false);
      setNewConfigName('');
      toast.success('方案创建成功');
    } catch (err) {
      toast.error('创建方案失败');
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('确定要删除这个方案吗？')) {
      try {
        await deleteConfig(id);
        toast.success('方案已删除');
      } catch (err) {
        toast.error('删除方案失败');
      }
    }
  };

  return (
    <div>
      <h2 className="mb-4">方案管理</h2>

      {error && toast.error(error)}

      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <strong>方案列表</strong>
          <Button variant="primary" size="sm" onClick={() => setShowCreateModal(true)}>
            新建方案
          </Button>
        </Card.Header>
        <Card.Body>
          <Table striped bordered hover>
            <thead>
              <tr>
                <th>方案名称</th>
                <th>创建时间</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {configs.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-muted">
                    {loading ? '加载中...' : '暂无方案'}
                  </td>
                </tr>
              )}
              {configs.map((config) => (
                <tr key={config.id}>
                  <td><strong>{config.name}</strong></td>
                  <td>{config.created_at || '-'}</td>
                  <td>{config.updated_at || '-'}</td>
                  <td>
                    <div className="d-flex gap-2">
                      <Button variant="info" size="sm">
                        编辑
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(config.id)}
                        disabled={loading}
                      >
                        删除
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>

      {/* 创建方案模态框 */}
      <Modal show={showCreateModal} onHide={() => setShowCreateModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>新建方案</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>方案名称</Form.Label>
              <Form.Control
                type="text"
                placeholder="输入方案名称"
                value={newConfigName}
                onChange={(e) => setNewConfigName(e.target.value)}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
            取消
          </Button>
          <Button
            variant="primary"
            onClick={handleCreate}
            disabled={!newConfigName || loading}
          >
            创建
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

