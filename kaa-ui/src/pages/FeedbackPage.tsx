import { useState } from 'react';
import { Card, Button, Form } from 'react-bootstrap';
import { call } from '../lib/rpc';
import { useToast } from '../lib/toast';

export default function FeedbackPage() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [uploadLogs, setUploadLogs] = useState(true);
  const [progress, setProgress] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    setProgress([]);

    try {
      // 生成 id（预留用于后续流式进度）
      // const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      
      // 监听流式响应
      call('reports.save', {
        title,
        description,
        upload: uploadLogs,
      }).then(() => {
        toast.success('反馈提交成功！感谢您的反馈。');
        setLoading(false);
        setTitle('');
        setDescription('');
      }).catch((err) => {
        toast.error(err.message || '提交失败');
        setLoading(false);
      });

      // TODO: 实现流式进度展示
      // 当前简化版本直接等待完成
    } catch (err: any) {
      toast.error(err.message || '提交失败');
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="mb-4">问题反馈</h2>

      <Card className="mb-4">
        <Card.Header>
          <strong>提交问题报告</strong>
        </Card.Header>
        <Card.Body>
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>标题</Form.Label>
              <Form.Control
                type="text"
                placeholder="简短描述问题"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>详细描述</Form.Label>
              <Form.Control
                as="textarea"
                rows={8}
                placeholder="详细描述遇到的问题、复现步骤等"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                label="包含日志文件（推荐）"
                checked={uploadLogs}
                onChange={(e) => setUploadLogs(e.target.checked)}
              />
            </Form.Group>

            <Button variant="primary" type="submit" disabled={loading}>
              {loading ? '提交中...' : '提交反馈'}
            </Button>
          </Form>
        </Card.Body>
      </Card>

      {progress.length > 0 && (
        <Card>
          <Card.Header>
            <strong>处理进度</strong>
          </Card.Header>
          <Card.Body>
            <div className="font-monospace" style={{ whiteSpace: 'pre-wrap' }}>
              {progress.join('\n')}
            </div>
          </Card.Body>
        </Card>
      )}
    </div>
  );
}

