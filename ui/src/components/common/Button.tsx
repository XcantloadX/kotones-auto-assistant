/** @jsxImportSource @emotion/react */
import { css } from '@emotion/react';
import styled from '@emotion/styled';
import React from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'destructive' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
}

const StyledButton = styled.button<{
  $variant: ButtonVariant;
  $size: ButtonSize;
  $fullWidth: boolean;
}>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: none;
  cursor: pointer;
  font-family: var(--font-system);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  white-space: nowrap;
  user-select: none;
  position: relative;

  ${({ $fullWidth }) => $fullWidth && 'width: 100%;'}

  /* Sizes */
  ${({ $size }) => {
    switch ($size) {
      case 'sm':
        return css`
          font-size: var(--font-size-sm);
          padding: 4px 10px;
          height: 24px;
        `;
      case 'lg':
        return css`
          font-size: var(--font-size-md);
          padding: 8px 20px;
          height: 38px;
        `;
      default: // md
        return css`
          font-size: var(--font-size-base);
          padding: 5px 14px;
          height: 30px;
        `;
    }
  }}

  /* Variants */
  ${({ $variant }) => {
    switch ($variant) {
      case 'primary':
        return css`
          background: var(--color-accent);
          color: white;
          &:hover:not(:disabled) { background: var(--color-accent-hover); }
          &:active:not(:disabled) { transform: scale(0.98); opacity: 0.9; }
        `;
      case 'destructive':
        return css`
          background: var(--color-red);
          color: white;
          &:hover:not(:disabled) { opacity: 0.9; }
          &:active:not(:disabled) { transform: scale(0.98); opacity: 0.8; }
        `;
      case 'ghost':
        return css`
          background: transparent;
          color: var(--color-accent);
          &:hover:not(:disabled) { background: var(--bg-hover); }
          &:active:not(:disabled) { background: rgba(0, 122, 255, 0.1); }
        `;
      default: // secondary
        return css`
          background: var(--bg-tertiary);
          color: var(--text-primary);
          border: 1px solid var(--border-medium);
          &:hover:not(:disabled) { background: var(--bg-hover); border-color: var(--border-input); }
          &:active:not(:disabled) { transform: scale(0.98); }
        `;
    }
  }}

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
`;

const Spinner = styled.span`
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

export const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  loading = false,
  fullWidth = false,
  children,
  disabled,
  ...props
}) => {
  return (
    <StyledButton
      $variant={variant}
      $size={size}
      $fullWidth={fullWidth}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </StyledButton>
  );
};
