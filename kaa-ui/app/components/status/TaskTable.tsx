import React from "react";
import { Table } from "react-bootstrap";
import { useRunStore } from "../../stores/runStore";

export default function TaskTable() {
  const { tasks } = useRunStore();
  
  return (
    <div className="card">
      <Table hover responsive className="mb-0">
        <thead className="table-light">
          <tr>
            <th>任务</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.name}>
              <td className="align-middle">
                <strong>{t.name}</strong>
              </td>
              <td className="align-middle">
                {t.status_text}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
} 