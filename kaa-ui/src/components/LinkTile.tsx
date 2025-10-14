import { Link } from 'react-router-dom';
import { Card } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChevronRight } from '@fortawesome/free-solid-svg-icons';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';
import './LinkTile.css';

interface LinkTileProps {
  to: string;
  title: string;
  description?: string;
  icon?: IconProp;
}

/**
 * Windows 11 FluentUI 风格的磁贴，专用于链接跳转。
 * @param to - 链接地址
 * @param title - 标题
 * @param description - 描述
 * @param icon - 图标
 * @returns 
 */
export default function LinkTile({ to, title, description, icon }: LinkTileProps) {
  return (
    <Link to={to} className="link-tile-wrapper">
      <Card className="link-tile">
        <Card.Body className="link-tile-body">
          <div className="link-tile-content">
            {icon && (
              <div className="link-tile-icon">
                <FontAwesomeIcon icon={icon} />
              </div>
            )}
            <div className="link-tile-text">
              <h5 className="link-tile-title">{title}</h5>
              {description && (
                <p className="link-tile-description">{description}</p>
              )}
            </div>
          </div>
          <div className="link-tile-arrow">
            <FontAwesomeIcon icon={faChevronRight} />
          </div>
        </Card.Body>
      </Card>
    </Link>
  );
}

