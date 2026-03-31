/** @jsxImportSource @emotion/react */
import styled from '@emotion/styled';
import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
}

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
`;

const Label = styled.label`
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
`;

const StyledInput = styled.input`
  background: var(--bg-secondary);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  padding: 5px 10px;
  font-family: var(--font-system);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  height: 30px;
  transition: border-color var(--transition-fast);
  width: 100%;

  &::placeholder {
    color: var(--text-tertiary);
  }

  &:focus {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: 0 0 0 3px var(--color-accent-light);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &[type="number"] {
    -moz-appearance: textfield;
    &::-webkit-inner-spin-button,
    &::-webkit-outer-spin-button {
      -webkit-appearance: none;
    }
  }
`;

const Hint = styled.p`
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
`;

const TextareaEl = styled.textarea`
  background: var(--bg-secondary);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  padding: 8px 10px;
  font-family: var(--font-system);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  resize: vertical;
  min-height: 80px;
  transition: border-color var(--transition-fast);
  width: 100%;

  &::placeholder {
    color: var(--text-tertiary);
  }

  &:focus {
    outline: none;
    border-color: var(--border-focus);
    box-shadow: 0 0 0 3px var(--color-accent-light);
  }
`;

export const Input: React.FC<InputProps> = ({ label, hint, ...props }) => {
  return (
    <Wrapper>
      {label && <Label>{label}</Label>}
      <StyledInput {...props} />
      {hint && <Hint>{hint}</Hint>}
    </Wrapper>
  );
};

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
}

export const Textarea: React.FC<TextareaProps> = ({ label, hint, ...props }) => {
  return (
    <Wrapper>
      {label && <Label>{label}</Label>}
      <TextareaEl {...props} />
      {hint && <Hint>{hint}</Hint>}
    </Wrapper>
  );
};
