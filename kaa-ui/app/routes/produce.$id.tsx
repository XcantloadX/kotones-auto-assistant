import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { Button, Form, Alert, Container } from "react-bootstrap";
import { useImmer } from "use-immer";
import ProDropdown from "../components/common/ProDropdown";
import * as api from "../services/api/produce";

export default function ProduceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [solution, updateSolution] = useImmer<api.ProduceSolution | null>(null);
  const [idols, setIdols] = useState<api.IdolOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showKotoneWarning, setShowKotoneWarning] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      if (!id) return;
      try {
        const [solutionData, idolList] = await Promise.all([
          api.getSolution(id),
          api.listIdols()
        ]);
        updateSolution(solutionData);
        setIdols(idolList);
        
        // 检查藤田ことね警告
        const hasKotone = solutionData.data.idol && idolList.find(i => i.value === solutionData.data.idol)?.label.includes("藤田ことね");
        const isStrictMode = solutionData.data.recommend_card_detection_mode === "strict";
        setShowKotoneWarning(Boolean(hasKotone && !isStrictMode));
      } catch (error) {
        console.error("加载培育方案失败:", error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [id, updateSolution]);

  const updateDataField = (field: keyof api.ProduceData, value: any) => {
    if (!solution) return;
    
    updateSolution(draft => {
      if (draft) {
        (draft.data as any)[field] = value;
      }
    });

    // 检查藤田ことね警告
    if (field === "idol" || field === "recommend_card_detection_mode") {
      const selectedIdol = field === "idol" ? value : solution.data.idol;
      const detectionMode = field === "recommend_card_detection_mode" ? value : solution.data.recommend_card_detection_mode;
      const hasKotone = selectedIdol && idols.find(i => i.value === selectedIdol)?.label.includes("ことね");
      const isStrictMode = detectionMode === "strict";
      setShowKotoneWarning(Boolean(hasKotone && !isStrictMode));
    }
  };

  const updateBasicField = (field: keyof api.ProduceSolution, value: any) => {
    updateSolution(draft => {
      if (draft) {
        (draft as any)[field] = value;
      }
    });
  };

  const save = async () => {
    if (!solution || !id) return;
    setSaving(true);
    try {
      await api.updateSolution(id, solution);
      alert("保存成功！");
    } catch (error) {
      console.error("保存失败:", error);
      alert("保存失败！");
    } finally {
      setSaving(false);
    }
  };

  const goBack = () => {
    navigate("/produce");
  };

  if (loading) {
    return <div>加载中...</div>;
  }

  if (!solution) {
    return <div>培育方案不存在</div>;
  }

  return (
    <Container fluid className="p-3">
      {/* 标题栏 */}
      <div className="d-flex align-items-center mb-4">
        <Button 
          variant="outline-secondary" 
          size="sm" 
          onClick={goBack}
          className="me-3"
          style={{ width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          ←
        </Button>
        <h2 className="mb-0 flex-grow-1">编辑培育方案</h2>
        <Button variant="primary" onClick={save} disabled={saving}>
          {saving ? "保存中..." : "保存"}
        </Button>
      </div>

      {showKotoneWarning && (
        <Alert variant="warning" className="mb-3">
          使用「藤田ことね」进行培育时，确保将「推荐卡检测模式」设置为「严格模式」
        </Alert>
      )}

      {/* 表单 */}
      <div style={{ maxWidth: '600px' }}>
        <Form.Group className="mb-3">
          <Form.Label>方案名称</Form.Label>
          <Form.Control
            value={solution.name}
            onChange={(e) => updateBasicField("name", e.target.value)}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>方案描述</Form.Label>
          <Form.Control
            as="textarea"
            rows={3}
            value={solution.description || ""}
            onChange={(e) => updateBasicField("description", e.target.value)}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>培育模式</Form.Label>
          <Form.Select
            value={solution.data.mode}
            onChange={(e) => updateDataField("mode", e.target.value as api.ProduceData["mode"])}
          >
            <option value="regular">Regular (~30min)</option>
            <option value="pro">Pro (~1h)</option>
            <option value="master">Master</option>
          </Form.Select>
          <Form.Text className="text-muted">
            进行一次 REGULAR 培育需要 ~30min，进行一次 PRO 培育需要 ~1h（具体视设备性能而定）。
          </Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>选择要培育的偶像</Form.Label>
          <ProDropdown
            value={solution.data.idol}
            onChange={(value) => updateDataField("idol", value)}
            options={idols}
            placeholder="请选择偶像"
            search={true}
            searchFn={(option, query) => {
              const q = query.toLowerCase();
              return option.label.toLowerCase().includes(q) || 
                     option.value.toLowerCase().includes(q);
            }}
          />
          <Form.Text className="text-muted">
            要培育偶像的 IdolCardSkin.id。支持按偶像名称或ID搜索。
          </Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="auto_set_memory"
            label="自动编成回忆"
            checked={solution.data.auto_set_memory}
            onChange={(e) => updateDataField("auto_set_memory", e.target.checked)}
          />
          <Form.Text className="text-muted">
            是否自动编成回忆。此选项优先级高于回忆编成编号。
          </Form.Text>
        </Form.Group>

        {!solution.data.auto_set_memory && (
          <Form.Group className="mb-3">
            <Form.Label>回忆编成编号</Form.Label>
            <Form.Select
              value={solution.data.memory_set || ""}
              onChange={(e) => updateDataField("memory_set", e.target.value ? parseInt(e.target.value) : null)}
            >
              <option value="">请选择</option>
              {Array.from({ length: 10 }, (_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}</option>
              ))}
            </Form.Select>
            <Form.Text className="text-muted">
              要使用的回忆编成编号，从 1 开始。
            </Form.Text>
          </Form.Group>
        )}

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="auto_set_support_card"
            label="自动编成支援卡"
            checked={solution.data.auto_set_support_card}
            onChange={(e) => updateDataField("auto_set_support_card", e.target.checked)}
          />
          <Form.Text className="text-muted">
            是否自动编成支援卡。此选项优先级高于支援卡编成编号。
          </Form.Text>
        </Form.Group>

        {!solution.data.auto_set_support_card && (
          <Form.Group className="mb-3">
            <Form.Label>支援卡编成编号</Form.Label>
            <Form.Select
              value={solution.data.support_card_set || ""}
              onChange={(e) => updateDataField("support_card_set", e.target.value ? parseInt(e.target.value) : null)}
            >
              <option value="">请选择</option>
              {Array.from({ length: 10 }, (_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}</option>
              ))}
            </Form.Select>
            <Form.Text className="text-muted">
              要使用的支援卡编成编号，从 1 开始。
            </Form.Text>
          </Form.Group>
        )}

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="use_pt_boost"
            label="使用支援强化 Pt 提升"
            checked={solution.data.use_pt_boost}
            onChange={(e) => updateDataField("use_pt_boost", e.target.checked)}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="use_note_boost"
            label="使用笔记数提升"
            checked={solution.data.use_note_boost}
            onChange={(e) => updateDataField("use_note_boost", e.target.checked)}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="follow_producer"
            label="关注租借了支援卡的制作人"
            checked={solution.data.follow_producer}
            onChange={(e) => updateDataField("follow_producer", e.target.checked)}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>文化课自习时选项</Form.Label>
          <Form.Select
            value={solution.data.self_study_lesson}
            onChange={(e) => updateDataField("self_study_lesson", e.target.value as api.ProduceData["self_study_lesson"])}
          >
            <option value="dance">舞蹈</option>
            <option value="visual">形象</option>
            <option value="vocal">声乐</option>
          </Form.Select>
          <Form.Text className="text-muted">自习课类型。</Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="prefer_lesson_ap"
            label="SP 课程优先"
            checked={solution.data.prefer_lesson_ap}
            onChange={(e) => updateDataField("prefer_lesson_ap", e.target.checked)}
          />
          <Form.Text className="text-muted">
            优先 SP 课程。启用后，若出现 SP 课程，则会优先执行 SP 课程，而不是推荐课程。若出现多个 SP 课程，随机选择一个。
          </Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>行动优先级</Form.Label>
          <ProDropdown
            multiple
            value={solution.data.actions_order}
            onChange={(value) => updateDataField("actions_order", value)}
            options={api.ACTION_OPTIONS}
            placeholder="请选择行动优先级"
          />
          <Form.Text className="text-muted">
            每一周的行动将会按这里设置的优先级执行。
          </Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>推荐卡检测模式</Form.Label>
          <Form.Select
            value={solution.data.recommend_card_detection_mode}
            onChange={(e) => updateDataField("recommend_card_detection_mode", e.target.value as api.RecommendCardDetectionMode)}
          >
            {api.DETECTION_MODE_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Form.Select>
          <Form.Text className="text-muted">
            推荐卡检测模式。严格模式下，识别速度会降低，但识别准确率会提高。
          </Form.Text>
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="use_ap_drink"
            label="AP 不足时自动使用 AP 饮料"
            checked={solution.data.use_ap_drink}
            onChange={(e) => updateDataField("use_ap_drink", e.target.checked)}
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Check
            type="checkbox"
            id="skip_commu"
            label="检测并跳过交流"
            checked={solution.data.skip_commu}
            onChange={(e) => updateDataField("skip_commu", e.target.checked)}
          />
        </Form.Group>
      </div>
    </Container>
  );
} 