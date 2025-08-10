import { useEffect, useState } from "react";
import { Button, Form, Table } from "react-bootstrap";
import * as api from "../services/api/produce";

export default function ProducePage() {
  const [items, setItems] = useState<api.ProduceSolution[]>([]);
  const [name, setName] = useState("");

  const load = async () => {
    const list = await api.listSolutions();
    setItems(list);
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!name) return;
    await api.createSolution(name);
    setName("");
    load();
  };

  const save = async (item: api.ProduceSolution) => {
    await api.updateSolution(item.id, item);
    load();
  };

  const remove = async (id: string) => {
    await api.deleteSolution(id);
    load();
  };

  return (
    <div className="vstack gap-2">
      <div className="d-flex gap-2">
        <Form.Control value={name} onChange={(e) => setName(e.target.value)} placeholder="新方案名称" />
        <Button onClick={create}>新建</Button>
      </div>
      <Table bordered size="sm">
        <thead>
          <tr>
            <th>名称</th>
            <th>模式</th>
            <th>自习</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id}>
              <td>
                <Form.Control value={it.name} onChange={(e) => (it.name = e.target.value)} />
              </td>
              <td>
                <Form.Select value={it.data.mode} onChange={(e) => (it.data.mode = e.target.value as api.ProduceData["mode"]) }>
                  <option value="regular">regular</option>
                  <option value="pro">pro</option>
                  <option value="master">master</option>
                </Form.Select>
              </td>
              <td>
                <Form.Select value={it.data.self_study_lesson} onChange={(e) => (it.data.self_study_lesson = e.target.value as api.ProduceData["self_study_lesson"]) }>
                  <option value="dance">dance</option>
                  <option value="visual">visual</option>
                  <option value="vocal">vocal</option>
                </Form.Select>
              </td>
              <td className="d-flex gap-2">
                <Button size="sm" variant="success" onClick={() => save(it)}>
                  保存
                </Button>
                <Button size="sm" variant="outline-danger" onClick={() => remove(it.id)}>
                  删除
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
} 