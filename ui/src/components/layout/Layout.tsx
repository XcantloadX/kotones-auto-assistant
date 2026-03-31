/** @jsxImportSource @emotion/react */
import styled from '@emotion/styled';
import React from 'react';
import { useAppStore } from '../../store/appStore';
import { useConnectionStore } from '../../store/connectionStore';

interface NavItem {
  id: string;
  label: string;
  icon: string;
}

const navItems: NavItem[] = [
  { id: 'status', label: '状态', icon: '◉' },
  { id: 'tasks', label: '任务', icon: '▶' },
  { id: 'settings', label: '设置', icon: '⚙' },
  { id: 'produce', label: '方案', icon: '★' },
  { id: 'feedback', label: '反馈', icon: '✉' },
  { id: 'update', label: '更新', icon: '↑' },
];

const AppLayout = styled.div`
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
`;

const Sidebar = styled.nav`
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  padding: var(--space-4) var(--space-3);
  gap: var(--space-1);
`;

const AppTitle = styled.div`
  padding: var(--space-3) var(--space-3) var(--space-5);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-secondary);
  letter-spacing: 0.02em;
`;

const NavItemEl = styled.button<{ $active: boolean }>`
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 7px var(--space-3);
  border: none;
  border-radius: var(--radius-md);
  background: ${({ $active }) => ($active ? 'var(--bg-selected)' : 'transparent')};
  color: ${({ $active }) => ($active ? 'var(--text-accent)' : 'var(--text-primary)')};
  font-size: var(--font-size-base);
  font-weight: ${({ $active }) => ($active ? 'var(--font-weight-medium)' : 'var(--font-weight-regular)')};
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
  width: 100%;
  font-family: var(--font-system);

  &:hover {
    background: ${({ $active }) => ($active ? 'var(--bg-selected)' : 'var(--bg-hover)')};
  }
`;

const NavIcon = styled.span`
  width: 18px;
  text-align: center;
  font-size: 14px;
  line-height: 1;
`;

const MainContent = styled.main`
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
`;

const StatusBar = styled.div`
  margin-top: auto;
  padding: var(--space-3);
  border-top: 1px solid var(--border-light);
`;

const ConnectionDot = styled.span<{ $status: string }>`
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: ${({ $status }) => {
    switch ($status) {
      case 'connected': return 'var(--color-green)';
      case 'connecting': return 'var(--color-orange)';
      case 'error': return 'var(--color-red)';
      default: return 'var(--text-tertiary)';
    }
  }};
  margin-right: var(--space-1);
`;

const StatusText = styled.span`
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
`;

interface LayoutProps {
  children: React.ReactNode;
  version?: string;
}

export const Layout: React.FC<LayoutProps> = ({ children, version }) => {
  const { activeTab, setActiveTab } = useAppStore();
  const { status } = useConnectionStore();

  const statusLabel = {
    connected: '已连接',
    connecting: '连接中...',
    disconnected: '已断开',
    error: '连接错误',
  }[status];

  return (
    <AppLayout>
      <Sidebar>
        <AppTitle>
          琴音小助手
          {version && <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}> {version}</span>}
        </AppTitle>
        {navItems.map(item => (
          <NavItemEl
            key={item.id}
            $active={activeTab === item.id}
            onClick={() => setActiveTab(item.id)}
          >
            <NavIcon>{item.icon}</NavIcon>
            {item.label}
          </NavItemEl>
        ))}
        <StatusBar>
          <ConnectionDot $status={status} />
          <StatusText>{statusLabel}</StatusText>
        </StatusBar>
      </Sidebar>
      <MainContent>
        {children}
      </MainContent>
    </AppLayout>
  );
};

export const PageContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
`;

export const PageTitle = styled.h1`
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  letter-spacing: -0.01em;
`;

export const PageSubtitle = styled.p`
  font-size: var(--font-size-base);
  color: var(--text-secondary);
`;
