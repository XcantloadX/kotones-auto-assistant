import { useState, useEffect } from 'react';
import { Card, Button, Form, Alert } from 'react-bootstrap';
import { call, on } from '../lib/rpc';
import { useToast } from '../lib/toast';
import Breadcrumb from '../components/Breadcrumb';

export default function ScreenPage() {
  const [subscribed, setSubscribed] = useState(false);
  const [interval, setInterval] = useState(1000);
  const [imageData, setImageData] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    // 订阅屏幕帧推送
    const unsubscribe = on('screen/frame', (data: any) => {
      if (data.image) {
        setImageData(`data:image/jpeg;base64,${data.image}`);
      }
    });

    return () => {
      unsubscribe();
      if (subscribed) {
        handleUnsubscribe();
      }
    };
  }, []);

  useEffect(() => {
    if (error) {
      toast.error(error);
    }
  }, [error, toast]);

  const handleGrab = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await call<{ image: string }>('screen.grab');
      if (result.image) {
        setImageData(`data:image/jpeg;base64,${result.image}`);
      }
    } catch (err: any) {
      setError(err.message);
      toast.error(err.message || '抓取失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async () => {
    try {
      setLoading(true);
      setError(null);
      await call('screen.subscribe', { intervalMs: interval });
      setSubscribed(true);
    } catch (err: any) {
      setError(err.message);
      toast.error(err.message || '订阅失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUnsubscribe = async () => {
    try {
      setLoading(true);
      setError(null);
      await call('screen.unsubscribe');
      setSubscribed(false);
    } catch (err: any) {
      setError(err.message);
      toast.error(err.message || '取消订阅失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Breadcrumb items={[{ text: '屏幕监控' }]} />

      <Card className="mb-4">
        <Card.Header>
          <strong>控制面板</strong>
        </Card.Header>
        <Card.Body>
          <div className="d-flex gap-2 align-items-center mb-3">
            <Button variant="primary" onClick={handleGrab} disabled={loading || subscribed}>
              抓取一次
            </Button>
            
            {!subscribed ? (
              <>
                <Form.Control
                  type="number"
                  style={{ width: '120px' }}
                  value={interval}
                  onChange={(e) => setInterval(Number(e.target.value))}
                  min={100}
                  step={100}
                  disabled={loading}
                />
                <span className="text-muted">ms</span>
                <Button variant="success" onClick={handleSubscribe} disabled={loading}>
                  开始订阅
                </Button>
              </>
            ) : (
              <Button variant="danger" onClick={handleUnsubscribe} disabled={loading}>
                停止订阅
              </Button>
            )}
          </div>

          {subscribed && (
            <Alert variant="info" className="mb-0">
              正在以 {interval}ms 间隔推送屏幕画面
            </Alert>
          )}
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          <strong>屏幕画面</strong>
        </Card.Header>
        <Card.Body>
          {imageData ? (
            <img
              src={imageData}
              alt="Screen capture"
              className="img-fluid border"
              style={{ maxWidth: '100%', height: 'auto' }}
            />
          ) : (
            <div className="text-center text-muted py-5">
              暂无画面
            </div>
          )}
        </Card.Body>
      </Card>
    </div>
  );
}

