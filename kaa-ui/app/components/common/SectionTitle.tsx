import React from "react";

export const SectionTitle: React.FC<{ title: string; children?: React.ReactNode }> = ({ title, children }) => (
  <div className="d-flex align-items-center justify-content-between mb-2">
    <h6 className="mb-0">{title}</h6>
    <div>{children}</div>
  </div>
); 