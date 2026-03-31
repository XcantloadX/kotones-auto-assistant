/** @jsxImportSource @emotion/react */
import styled from '@emotion/styled';
import React from 'react';

interface CheckboxProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

const Label = styled.label<{ $disabled?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: ${({ $disabled }) => ($disabled ? 'not-allowed' : 'pointer')};
  opacity: ${({ $disabled }) => ($disabled ? 0.5 : 1)};
  user-select: none;
  font-size: var(--font-size-base);
  color: var(--text-primary);
`;

const HiddenInput = styled.input`
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
`;

const CheckboxBox = styled.span<{ $checked: boolean }>`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  min-width: 16px;
  border-radius: 4px;
  border: 1.5px solid ${({ $checked }) => ($checked ? 'transparent' : 'var(--border-input)')};
  background: ${({ $checked }) => ($checked ? 'var(--color-accent)' : 'var(--bg-secondary)')};
  transition: all var(--transition-fast);

  svg {
    display: ${({ $checked }) => ($checked ? 'block' : 'none')};
  }
`;

export const Checkbox: React.FC<CheckboxProps> = ({ label, checked, onChange, disabled }) => {
  return (
    <Label $disabled={disabled}>
      <HiddenInput
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        disabled={disabled}
      />
      <CheckboxBox $checked={checked}>
        <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
          <path
            d="M1 4L3.5 6.5L9 1"
            stroke="white"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </CheckboxBox>
      {label}
    </Label>
  );
};
