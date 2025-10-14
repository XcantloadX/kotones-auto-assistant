import { Link, useLocation } from 'react-router-dom';
import React, { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import './Sidebar.css';
import {
  faChartLine,
  faListCheck,
  faGear,
  faComments,
  faBell,
  faDesktop,
  faBars,
  faAnglesLeft,
  faRotateLeft,
} from '@fortawesome/free-solid-svg-icons';
import { useMessageBox } from '../lib/messagebox';

const menuItems = [
    { path: '/', label: '状态', icon: faChartLine },
    { path: '/tasks', label: '任务', icon: faListCheck },
    { path: '/settings', label: '设置', icon: faGear },
    { path: '/feedback', label: '反馈', icon: faComments },
    { path: '/updates', label: '更新', icon: faBell },
    { path: '/screen', label: '屏幕', icon: faDesktop },
];

export function Sidebar() {
    const location = useLocation();
    const [collapsed, setCollapsed] = useState(false);
    const msgbox = useMessageBox();

    const toggleSidebar = () => {
        setCollapsed(!collapsed);
    };
    
    const handleBackToOldVersionClick = async (e: React.MouseEvent<HTMLAnchorElement>) => {
        e.preventDefault();
        const confirmed = await msgbox.ask('是否切换回旧版 UI？这需要重启 kaa。', '请确认');
        if (confirmed) {
          window.open(e.currentTarget.href, '_blank');
        }
    };

    return (
        <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          {!collapsed && <h1 className="sidebar-title">琴音小助手</h1>}
          <button 
            className="sidebar-toggle" 
            onClick={toggleSidebar}
            aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
          >
            <FontAwesomeIcon icon={collapsed ? faBars : faAnglesLeft} />
          </button>
        </div>
        
        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
              title={collapsed ? item.label : ''}
            >
              <span className="sidebar-nav-icon">
                <FontAwesomeIcon icon={item.icon} />
              </span>
              {!collapsed && <span className="sidebar-nav-label">{item.label}</span>}
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          <a 
            href="http://127.0.0.1:7860" 
            target="_blank" 
            rel="noopener noreferrer"
            className="sidebar-footer-link"
            title={collapsed ? '回到旧版' : ''}
            onClick={handleBackToOldVersionClick}
          >
            <span className="sidebar-nav-icon">
              <FontAwesomeIcon icon={faRotateLeft} />
            </span>
            {!collapsed && <span>回到旧版</span>}
          </a>
        </div>
      </aside>
    );
}
