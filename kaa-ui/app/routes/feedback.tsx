import { useState } from "react";
import { Button, Form } from "react-bootstrap";
import { post, get } from "../services/http";

export default function FeedbackPage() {
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [upload, setUpload] = useState(false);
  const [msg, setMsg] = useState<string | undefined>();

  const submit = async () => {
    const res = await post<{ ok: boolean; message: string }>(`/api/v1/reports/bug?title=${encodeURIComponent(title)}&description=${encodeURIComponent(desc)}&upload=${upload}`);
    setMsg(res.message);
  };

  const exportLogs = async () => {
    const text = await get<string>("/api/v1/reports/logs.zip");
    setMsg(text);
  };

  const exportDumps = async () => {
    const text = await get<string>("/api/v1/reports/dumps.zip");
    setMsg(text);
  };

  return (
    <div className="row g-3">
      <div className="col-12">
        <div className="card"><div className="card-body">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <h6 className="mb-0">反馈</h6>
            <div className="d-flex gap-2">
              <Button size="sm" variant="outline-secondary" onClick={exportLogs}><i className="bi bi-archive me-1"/>导出日志</Button>
              <Button size="sm" variant="outline-secondary" onClick={exportDumps}><i className="bi bi-archive me-1"/>导出数据</Button>
            </div>
          </div>
          <Form className="vstack gap-2">
            <Form.Control placeholder="标题" value={title} onChange={(e) => setTitle(e.target.value)} />
            <Form.Control as="textarea" rows={10} placeholder="描述" value={desc} onChange={(e) => setDesc(e.target.value)} />
            <Form.Check type="checkbox" label="上传到服务器（示例）" checked={upload} onChange={(e) => setUpload(e.target.checked)} />
            <div>
              <Button onClick={submit}><i className="bi bi-cloud-upload me-1"/>提交</Button>
            </div>
          </Form>
        </div></div>
      </div>
      <div className="col-12">
        <div className="card"><div className="card-body">
          <div className="fw-bold mb-2">进度/结果</div>
          <div className="bg-body-tertiary rounded p-3" style={{ minHeight: 76 }}>
            <div className="text-secondary">{msg ?? "等待操作…"}</div>
          </div>
        </div></div>
      </div>
    </div>
  );
} 