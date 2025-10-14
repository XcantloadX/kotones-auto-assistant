import { useEffect, useState } from 'react';
import { Card, Button, Form } from 'react-bootstrap';
import { useConfigStore } from '../stores/useConfigStore';
import { useToast } from '../lib/toast';
import Breadcrumb from '../components/Breadcrumb';
import LinkTile from '../components/LinkTile';
import { faFileLines } from '@fortawesome/free-solid-svg-icons';

export default function SettingsPage() {
  const { config, loading, error, fetchConfig, saveConfig, reloadConfig } = useConfigStore();
  const [formData, setFormData] = useState<any>({});
  const toast = useToast();

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  useEffect(() => {
    if (config) {
      setFormData(config);
    }
  }, [config]);

  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error, toast]);

  const handleSave = async () => {
    try {
      await saveConfig(formData);
      toast.success('配置保存成功！');
    } catch (err) {
      toast.error('保存配置失败');
    }
  };

  const handleReload = async () => {
    try {
      await reloadConfig();
      toast.success('配置重新加载完成');
    } catch (err) {
      toast.error('重新加载配置失败');
    }
  };

  if (loading && !config) {
    return <div>加载配置中...</div>;
  }

  return (
    <div>
      <Breadcrumb items={[{ text: '设置' }]} />

      <div className="mb-4">
        <LinkTile
          to="/produce"
          title="培育方案"
          description="添加、修改或删除 kaa 的培育方案"
          icon={faFileLines}
        />
      </div>

      <Card className="mb-4">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <strong>配置选项</strong>
          <div className="d-flex gap-2">
            <Button variant="secondary" size="sm" onClick={handleReload} disabled={loading}>
              重新加载
            </Button>
            <Button variant="primary" size="sm" onClick={handleSave} disabled={loading}>
              保存配置
            </Button>
          </div>
        </Card.Header>
        <Card.Body>
          {!config ? (
            <p className="text-muted">无法加载配置</p>
          ) : (
            <Form>
              <Form.Group className="mb-3">
                <Form.Label>配置 JSON（临时简化版）</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={20}
                  value={JSON.stringify(formData, null, 2)}
                  onChange={(e) => {
                    try {
                      setFormData(JSON.parse(e.target.value));
                    } catch {
                      // 忽略解析错误
                    }
                  }}
                />
                <Form.Text className="text-muted">
                  编辑 JSON 配置（后续将提供可视化编辑界面）
                </Form.Text>
              </Form.Group>
            </Form>
          )}
        </Card.Body>
      </Card>
    </div>
  );
}

