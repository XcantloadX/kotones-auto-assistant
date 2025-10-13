import { BrowserRouter, Routes, Route } from 'react-router-dom';
import React from 'react';
import { useConnectionStore } from './stores/useConnectionStore';
import StatusPage from './pages/StatusPage.tsx';
import TasksPage from './pages/TasksPage.tsx';
import SettingsPage from './pages/SettingsPage.tsx';
import ProducePage from './pages/ProducePage.tsx';
import FeedbackPage from './pages/FeedbackPage.tsx';
import UpdatesPage from './pages/UpdatesPage.tsx';
import ScreenPage from './pages/ScreenPage.tsx';
import './App.css';
import { useToast } from './lib/toast';
import { rpcClient } from './lib/rpc';
import { MessageBoxProvider } from './lib/messagebox.tsx';
import { Sidebar } from './components/Sidebar.tsx';

function AppContent() {
  // 连接状态仅用于后续可能的 UI 控制，暂不直接渲染
  useConnectionStore((state) => state.connected);

  return (
    <div className="app-container">
      {/* 侧边栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <main className="main-content">

        <div className="content-wrapper">
          <Routes>
            <Route path="/" element={<StatusPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/produce" element={<ProducePage />} />
            <Route path="/feedback" element={<FeedbackPage />} />
            <Route path="/updates" element={<UpdatesPage />} />
            <Route path="/screen" element={<ScreenPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function App() {
  function RPCToastBinder() {
    const toast = useToast();
    // 绑定全局 RPC 错误处理，UI 决定如何提示
    React.useEffect(() => {
      const unsubscribe = rpcClient.onError((error, ctx) => {
        switch (ctx.type) {
          case 'connect-failed':
            toast.error('无法连接到服务器，请检查后端是否启动', '连接失败');
            break;
          case 'connect-error':
            toast.error('连接异常', '连接失败');
            break;
          case 'timeout':
            toast.error(`请求超时：${ctx.method ?? ''}`, '请求失败');
            break;
          case 'stream-error':
          case 'rpc-error':
          default:
            toast.error(error.message, '请求失败');
            break;
        }
      });
      return () => unsubscribe();
    }, [toast]);
    return null;
  }

  return (
    <BrowserRouter>
      <MessageBoxProvider>
        <RPCToastBinder />
        <AppContent />
      </MessageBoxProvider>
    </BrowserRouter>
  );
}

export default App;
