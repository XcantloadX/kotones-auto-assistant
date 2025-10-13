import { useEffect, useState } from 'react';
import { Button, Modal, Form } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEdit, faTrash } from '@fortawesome/free-solid-svg-icons';
import { useProduceStore } from '../stores/useProduceStore';
import { useToast } from '../lib/toast';
import Breadcrumb from '../components/Breadcrumb';

export default function ProducePage() {
  const { configs, loading, error, fetchConfigs, createConfig, deleteConfig } = useProduceStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');
  const toast = useToast();

  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error, toast]);

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
      <Breadcrumb items={[{ text: '方案管理' }]} />
      
      <div className="mb-4">
        <div className="d-flex align-items-center">
          <Button variant="primary" onClick={() => setShowCreateModal(true)}>
            新建方案
          </Button>
        </div>
      </div>

      <div className="mb-4">
        {configs.length === 0 && (
          <div className="text-center text-muted p-4">
            {loading ? '加载中...' : '暂无方案'}
          </div>
        )}

        {configs.map((config) => (
          <div key={config.id} className="d-flex align-items-center p-3 border rounded mb-2 bg-light">
            <div className="d-flex gap-2 me-3">
              <Button variant="primary" size="sm" title="编辑">
                <FontAwesomeIcon icon={faEdit} />
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => handleDelete(config.id)}
                disabled={loading}
                title="删除"
              >
                <FontAwesomeIcon icon={faTrash} />
              </Button>
            </div>
            <div className="flex-grow-1">
              <h6 className="mb-1"><strong>{config.name}</strong></h6>
            </div>
          </div>
        ))}
      </div>

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

