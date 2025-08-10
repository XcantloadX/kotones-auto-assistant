type Props = {
  title: string;
  enabled?: boolean;
  onToggle?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  showSwitch?: boolean;
  subtitle?: string;
};

export default function SectionTitle({ title, enabled = true, onToggle, showSwitch = false, subtitle }: Props) {
  return (
    <>
      <div className="d-flex align-items-center mb-2">
        {showSwitch && onToggle && (
          <div className="form-check form-switch d-inline-block me-1 mb-0">
            <input 
              className="form-check-input" 
              type="checkbox" 
              checked={enabled} 
              onChange={onToggle} 
            />
          </div>
        )}
        <div className={`fs-5 fw-bold ${!enabled && showSwitch ? 'text-secondary text-decoration-line-through' : ''}`}>
          {title}
        </div>
      </div>
      {subtitle && (
        <div className="text-secondary mb-3" style={{fontSize: '0.9rem'}}>{subtitle}</div>
      )}
    </>
  );
} 