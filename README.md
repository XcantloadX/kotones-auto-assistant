# KotonesAutoAssistant 琴音小助手
## 功能
* 自动日常，包括
    * 领取礼物（邮件）
    * 领取活动费
    * 领取工作奖励并自动重新安排工作
    * 自动竞赛挑战
* 低配版自动培育（目前仅限 Ruglar 模式）

## 安装&使用
对模拟器的要求：
* 分辨率：目前必须是 1280x720
* 系统版本：Android 10+（Q，API 29），这是游戏的要求


TODO

## 开发
> [!NOTE]
> 建议使用 VSCode 进行开发。
```bash
git clone https://github.com/XcantloadX/KotonesAutoAssistant.git
cd KotonesAutoAssistant
```

### 后端
```bash
python -m venv venv
source venv/bin/activate # Windows 系统: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements.dev.txt
python tools/make_resources.py
```
然后打开 VSCode 设置，搜索“SupportRestructured Text”并勾选。

### 前端
```bash
cd kotonebot-ui
npm install
npm run dev
```

### 截图
建议使用 [XnView MP](https://www.xnview.com/en/xnviewmp/) 进行截图裁剪工作。

XnView MP 可以方便的完成“打开图片 → 选区 → 裁剪图片 → 另存选取为文件”这一操作。
只需要提前设置好右键菜单：
![XnView MP 设置1](./images/xnview_setup1.png)

## 清单
- [ ] 提高课程/考试中检测推荐卡的准确率
- [ ] 微调 OCR 模型。目前 OCR 识别结果不太准确
- [ ] 支持多分辨率
- [ ] 尝试支持汉化版
- [ ] 截图：AI 辅助自动裁剪 + 命名文件