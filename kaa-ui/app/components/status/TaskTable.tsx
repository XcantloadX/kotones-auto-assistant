import React from "react";
import { Table } from "react-bootstrap";
import { useRunStore } from "../../stores/runStore";

export default function TaskTable() {
  const { tasks } = useRunStore();
  return (
    <div className="table-responsive">
      <Table bordered size="sm" className="align-middle">
        <thead className="table-light">
          <tr>
            <th>任务</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.name}>
              <td>{t.name}</td>
              <td>{t.status_text}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
} 