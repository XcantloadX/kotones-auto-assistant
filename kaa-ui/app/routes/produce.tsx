import { useEffect, useState } from "react";
import { Button, Form, Table, Modal } from "react-bootstrap";
import { useNavigate } from "react-router";
import * as api from "../services/api/produce";

export default function ProducePage() {
  const [items, setItems] = useState<api.ProduceSolution[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const navigate = useNavigate();

  const load = async () => {
    const list = await api.listSolutions();
    setItems(list);
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!newName.trim()) return;
    try {
      const newSolution = await api.createSolution(newName, newDescription);
      setNewName("");
      setNewDescription("");
      setShowModal(false);
      // 跳转到编辑页面
      navigate(`/produce/${newSolution.id}`);
    } catch (error) {
      console.error("创建培育方案失败:", error);
    }
  };

  const remove = async (id: string) => {
    await api.deleteSolution(id);
    load();
  };

  const edit = (id: string) => {
    navigate(`/produce/${id}`);
  };

  return (
    <div className="vstack gap-2">
      <div className="d-flex justify-content-start mb-3">
        <Button variant="primary" onClick={() => setShowModal(true)}>新建培育方案</Button>
      </div>
      
      <div className="card">
        <Table hover responsive className="mb-0">
          <thead className="table-light">
            <tr>
              <th style={{ width: '25%' }}>名称</th>
              <th style={{ width: '50%' }}>描述</th>
              <th style={{ width: '25%', textAlign: 'center' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={3} className="text-center py-4 text-muted">
                  暂无培育方案，点击上方按钮创建
                </td>
              </tr>
            ) : (
              items.map((it) => (
                <tr key={it.id}>
                  <td className="align-middle">
                    <strong>{it.name}</strong>
                  </td>
                  <td className="align-middle">
                    <span className="text-muted">
                      {it.description || "无描述"}
                    </span>
                  </td>
                  <td className="align-middle text-center">
                    <div className="d-flex gap-2 justify-content-center">
                      <Button size="sm" variant="outline-primary" onClick={() => edit(it.id)}>
                        编辑
                      </Button>
                      <Button size="sm" variant="outline-danger" onClick={() => remove(it.id)}>
                        删除
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
      </div>

      {/* 新建Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>新建培育方案</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>名称</Form.Label>
              <Form.Control
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="请输入方案名称"
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>描述</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="请输入方案描述（可选）"
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            取消
          </Button>
          <Button variant="primary" onClick={create}>
            确定
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
} 