/** @jsxImportSource @emotion/react */
import styled from '@emotion/styled';
import React from 'react';

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Card = styled.div`
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
`;

interface SectionProps {
  title?: string;
  children: React.ReactNode;
}

const SectionEl = styled.section`
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
`;

const SectionTitle = styled.h3`
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 11px;
`;

export const Section: React.FC<SectionProps> = ({ title, children }) => (
  <SectionEl>
    {title && <SectionTitle>{title}</SectionTitle>}
    {children}
  </SectionEl>
);

interface RadioGroupProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  options: { label: string; value: string }[];
  disabled?: boolean;
}

const RadioGroupWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
`;

const RadioGroupLabel = styled.label`
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
`;

const RadioOptions = styled.div`
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
`;

const RadioOption = styled.label<{ $disabled?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: ${({ $disabled }) => ($disabled ? 'not-allowed' : 'pointer')};
  opacity: ${({ $disabled }) => ($disabled ? 0.5 : 1)};
  font-size: var(--font-size-base);
`;

const RadioInput = styled.input`
  width: 16px;
  height: 16px;
  accent-color: var(--color-accent);
`;

export const RadioGroup: React.FC<RadioGroupProps> = ({
  label,
  value,
  onChange,
  options,
  disabled,
}) => {
  return (
    <RadioGroupWrapper>
      {label && <RadioGroupLabel>{label}</RadioGroupLabel>}
      <RadioOptions>
        {options.map(opt => (
          <RadioOption key={opt.value} $disabled={disabled}>
            <RadioInput
              type="radio"
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              disabled={disabled}
            />
            {opt.label}
          </RadioOption>
        ))}
      </RadioOptions>
    </RadioGroupWrapper>
  );
};

export const Divider = styled.hr`
  border: none;
  border-top: 1px solid var(--border-light);
  margin: var(--space-2) 0;
`;

export const FormRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
`;

export const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
`;
