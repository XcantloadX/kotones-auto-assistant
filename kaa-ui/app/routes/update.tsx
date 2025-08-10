import { useEffect, useState } from "react";
import { Button, Alert, Spinner, Card, Badge, Modal, Row, Col } from "react-bootstrap";
import { get, post } from "../services/http";

type VersionInfo = { 
  installed: string | null; 
  latest: string | null; 
  versions: string[]; 
  status?: string;
};

type InstallResponse = {
  ok: boolean;
  message: string;
};

export default function UpdatePage() {
  const [info, setInfo] = useState<VersionInfo>({ 
    installed: null, 
    latest: null, 
    versions: [] 
  });
  const [loading, setLoading] = useState(false);
  const [installLoading, setInstallLoading] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const [changelog, setChangelog] = useState<string>("");
  const [showInstallModal, setShowInstallModal] = useState(false);
  const [installMessage, setInstallMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [showLogModal, setShowLogModal] = useState(false);
  const [selectedVersionLog, setSelectedVersionLog] = useState<string>("");
  const [selectedVersionNumber, setSelectedVersionNumber] = useState<string>("");

  // 加载更新日志
  useEffect(() => {
    const loadChangelog = async () => {
      try {
        const data = await get<string>("/api/v1/update/changelog");
        setChangelog(data);
      } catch (error) {
        console.error("加载更新日志失败:", error);
        setChangelog("# 更新日志\n\n暂无更新日志信息。");
      }
    };
    loadChangelog();
  }, []);

  const loadVersionInfo = async () => {
    try {
      setLoading(true);
      setErrorMessage("");
      
      const data = await get<VersionInfo>("/api/v1/update/versions");
      setInfo(data);
      
      if (data.versions && data.versions.length > 0) {
        setShowVersions(true);
      } else {
        setErrorMessage("未找到可用版本");
        setShowVersions(false);
      }
    } catch (error) {
      console.error("载入版本信息失败:", error);
      setErrorMessage(`载入版本信息失败: ${error instanceof Error ? error.message : '未知错误'}`);
      setShowVersions(false);
    } finally {
      setLoading(false);
    }
  };

  const installVersion = async (version: string) => {
    try {
      setInstallLoading(true);
      setShowInstallModal(true);
      setInstallMessage(`正在安装版本 ${version}，请稍候...`);
      
      const response = await post<InstallResponse>(`/api/v1/update/install/${version}`);
      setInstallMessage(response.message);
      
      // 安装成功后，保持模态框显示，因为程序即将重启
    } catch (error) {
      console.error("安装失败:", error);
      setInstallMessage(`安装失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setInstallLoading(false);
    }
  };

  const viewVersionLog = (version: string) => {
    const versionLog = parseVersionLog(version);
    setSelectedVersionNumber(version);
    setSelectedVersionLog(versionLog);
    setShowLogModal(true);
  };

  const parseVersionLog = (version: string): string => {
    if (!changelog) return "暂无该版本的日志信息。";
    
    // 查找对应版本的日志段落
    const lines = changelog.split('\n');
    const versionLineIndex = lines.findIndex(line => 
      line.includes(`### v${version}`) || line.includes(`### ${version}`)
    );
    
    if (versionLineIndex === -1) {
      return "暂无该版本的日志信息。";
    }
    
    // 从版本标题开始，到下一个版本标题结束
    const startIndex = versionLineIndex;
    let endIndex = lines.length;
    
    for (let i = startIndex + 1; i < lines.length; i++) {
      if (lines[i].startsWith('### v') && lines[i] !== lines[startIndex]) {
        endIndex = i;
        break;
      }
    }
    
    return lines.slice(startIndex, endIndex).join('\n').trim();
  };

  const formatMarkdown = (text: string) => {
    return text
      .split('\n')
      .map((line, index) => {
        if (line.startsWith('# ')) {
          return <h1 key={index} className="h4 mt-3 mb-2">{line.slice(2)}</h1>;
        } else if (line.startsWith('## ')) {
          return <h2 key={index} className="h5 mt-3 mb-2">{line.slice(3)}</h2>;
        } else if (line.startsWith('### ')) {
          return <h3 key={index} className="h6 mt-2 mb-1 fw-bold">{line.slice(4)}</h3>;
        } else if (line.startsWith('* ')) {
          return <li key={index} className="small">{line.slice(2)}</li>;
        } else if (line.trim() === '') {
          return <br key={index} />;
        } else {
          return <p key={index} className="small mb-1">{line}</p>;
        }
      });
  };

  const isCurrentVersion = (version: string) => {
    return info.installed === version;
  };

  const isLatestVersion = (version: string) => {
    return info.latest === version;
  };

  return (
    <>
      <div className="vstack gap-3">
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0">版本管理</h5>
        </div>

        <div>
          <Button 
            variant="primary" 
            onClick={loadVersionInfo}
            disabled={loading}
          >
            {loading ? (
              <>
                <Spinner size="sm" className="me-2" />
                载入中...
              </>
            ) : (
              '载入信息'
            )}
          </Button>
        </div>

        {/* 错误信息 */}
        {errorMessage && (
          <Alert variant="danger">
            {errorMessage}
          </Alert>
        )}

        {/* 版本列表 */}
        {showVersions && info.versions.length > 0 && (
          <div className="d-flex justify-content-center">
            <div className="w-full">
              <Card>
                <Card.Header>
                  <h6 className="mb-0">可用版本 ({info.versions.length})</h6>
                </Card.Header>
                <Card.Body className="p-0">
                  <div className="list-group list-group-flush">
                    {info.versions.map((version, index) => (
                      <div key={version} className="list-group-item">
                        <Row className="align-items-center">
                          <Col>
                            <div className="d-flex align-items-center gap-2">
                              <span className="fw-medium">{version}</span>
                              {isCurrentVersion(version) && (
                                <Badge bg="success">当前版本</Badge>
                              )}
                              {isLatestVersion(version) && !isCurrentVersion(version) && (
                                <Badge bg="primary">最新版本</Badge>
                              )}
                            </div>
                          </Col>
                          <Col xs="auto">
                            <div className="d-flex gap-1">
                              <Button 
                                size="sm"
                                variant={isCurrentVersion(version) ? "outline-secondary" : "outline-primary"}
                                onClick={() => installVersion(version)}
                                disabled={installLoading || isCurrentVersion(version)}
                              >
                                {isCurrentVersion(version) ? "已安装" : "安装"}
                              </Button>
                              <Button 
                                size="sm"
                                variant="outline-info"
                                onClick={() => viewVersionLog(version)}
                              >
                                查看日志
                              </Button>
                            </div>
                          </Col>
                        </Row>
                      </div>
                    ))}
                  </div>
                </Card.Body>
              </Card>
            </div>
          </div>
        )}
      </div>

      {/* 全屏安装提示模态框 */}
      <Modal 
        show={showInstallModal} 
        backdrop="static" 
        keyboard={false}
        centered
        size="lg"
      >
        <Modal.Header>
          <Modal.Title>
            <i className="bi bi-download me-2"></i>
            版本安装
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="text-center py-4">
          {installLoading && (
            <div className="mb-3">
              <Spinner animation="border" size="sm" className="me-2" />
              <span>正在处理安装请求...</span>
            </div>
          )}
          <div className="alert alert-info">
            <i className="bi bi-info-circle me-2"></i>
            {installMessage}
          </div>
          {!installLoading && (
            <div className="text-muted small mt-3">
              <i className="bi bi-exclamation-triangle me-1"></i>
              安装完成后程序将自动重启，请勿关闭此窗口
            </div>
          )}
        </Modal.Body>
        {!installLoading && (
          <Modal.Footer>
            <Button 
              variant="secondary" 
              onClick={() => setShowInstallModal(false)}
            >
              关闭
            </Button>
          </Modal.Footer>
        )}
      </Modal>

      {/* 版本日志查看模态框 */}
      <Modal 
        show={showLogModal} 
        onHide={() => setShowLogModal(false)}
        centered
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            <i className="bi bi-journal-text me-2"></i>
            版本 {selectedVersionNumber} 更新日志
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {selectedVersionLog ? (
              formatMarkdown(selectedVersionLog)
            ) : (
              <div className="text-muted">暂无该版本的日志信息。</div>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowLogModal(false)}>
            关闭
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
} 