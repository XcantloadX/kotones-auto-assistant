/** @jsxImportSource @emotion/react */
import styled from '@emotion/styled';
import React from 'react';

type AlertVariant = 'info' | 'warning' | 'error' | 'success';

interface AlertProps {
  variant?: AlertVariant;
  children: React.ReactNode;
}

const variantConfig: Record<AlertVariant, { bg: string; border: string; color: string; icon: string }> = {
  info: {
    bg: 'rgba(0, 122, 255, 0.08)',
    border: 'rgba(0, 122, 255, 0.25)',
    color: 'var(--color-accent)',
    icon: 'ℹ',
  },
  warning: {
    bg: 'rgba(255, 149, 0, 0.1)',
    border: 'rgba(255, 149, 0, 0.3)',
    color: 'var(--color-orange)',
    icon: '⚠',
  },
  error: {
    bg: 'rgba(255, 59, 48, 0.08)',
    border: 'rgba(255, 59, 48, 0.25)',
    color: 'var(--color-red)',
    icon: '✕',
  },
  success: {
    bg: 'rgba(48, 209, 88, 0.08)',
    border: 'rgba(48, 209, 88, 0.25)',
    color: 'var(--color-green)',
    icon: '✓',
  },
};

const AlertBox = styled.div<{ $variant: AlertVariant }>`
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid ${({ $variant }) => variantConfig[$variant].border};
  background: ${({ $variant }) => variantConfig[$variant].bg};
  font-size: var(--font-size-sm);
  color: var(--text-primary);
`;

const Icon = styled.span<{ $variant: AlertVariant }>`
  font-style: normal;
  color: ${({ $variant }) => variantConfig[$variant].color};
  font-size: var(--font-size-md);
  line-height: 1.4;
  flex-shrink: 0;
`;

export const Alert: React.FC<AlertProps> = ({ variant = 'info', children }) => {
  return (
    <AlertBox $variant={variant}>
      <Icon $variant={variant}>{variantConfig[variant].icon}</Icon>
      <span>{children}</span>
    </AlertBox>
  );
};
