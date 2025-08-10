import { useEffect, useState } from "react";
import { Button, Table } from "react-bootstrap";
import { get, post } from "../services/http";

type VersionInfo = { installed: string | null; latest: string | null; versions: string[] };

export default function UpdatePage() {
  const [info, setInfo] = useState<VersionInfo>({ installed: null, latest: null, versions: [] });
  const [msg, setMsg] = useState<string | undefined>();

  const load = async () => {
    const d = await get<VersionInfo>("/api/v1/update/versions");
    setInfo(d);
  };

  useEffect(() => { load(); }, []);

  const install = async () => {
    const res = await post<{ ok: boolean; message: string }>("/api/v1/update/install");
    setMsg(res.message);
  };

  return (
    <div className="vstack gap-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="mb-0">更新</h6>
        <Button size="sm" onClick={install}><i className="bi bi-download me-1"/>安装</Button>
      </div>
      <Table bordered size="sm">
        <tbody>
          <tr><td>已安装</td><td>{info.installed ?? "-"}</td></tr>
          <tr><td>最新</td><td>{info.latest ?? "-"}</td></tr>
          <tr><td>可选版本</td><td>{info.versions.join(", ")}</td></tr>
        </tbody>
      </Table>
      {msg && <div className="text-muted small">{msg}</div>}
    </div>
  );
} 