import { Link } from 'react-router-dom';
import './Breadcrumb.css';

export interface BreadcrumbItem {
  text: string;
  link?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export default function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <h2 className="breadcrumb-container mb-4">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        const isCurrent = isLast;
        
        return (
          <span key={index} className="breadcrumb-item-wrapper">
            {index > 0 && <span className="breadcrumb-separator"> &gt; </span>}
            {item.link && !isCurrent ? (
              <Link to={item.link} className="breadcrumb-link">
                {item.text}
              </Link>
            ) : (
              <span className={isCurrent ? 'breadcrumb-current' : 'breadcrumb-text'}>
                {item.text}
              </span>
            )}
          </span>
        );
      })}
    </h2>
  );
}

