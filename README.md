# Reddit 监测工具

自动监控 Reddit 游戏开发相关社区，使用 Gemini AI 分析帖子相关性，将潜在客户信息推送到飞书群。

## 功能特点

- 🔍 自动抓取多个游戏开发相关 Subreddit 的新帖子
- 🤖 使用 Google Gemini AI 智能分析帖子相关性
- 💬 自动生成参考回复建议
- 📱 推送精美飞书卡片通知
- ⏰ GitHub Actions 每小时自动运行
- 💰 完全免费（使用 GitHub Actions 免费额度）

## 快速部署

### 1. Fork 本仓库

点击右上角 Fork 按钮，将仓库复制到你的账号下。

### 2. 配置 Secrets

进入你 Fork 后的仓库，点击 **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

添加以下两个 Secret：

| Name | Value |
|------|-------|
| `GEMINI_API_KEY` | 你的 Google Gemini API Key |
| `FEISHU_WEBHOOK_URL` | 飞书群机器人的 Webhook URL |

#### 获取 Gemini API Key

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 点击 "Create API Key"
3. 复制生成的 Key

#### 获取飞书 Webhook URL

1. 打开飞书群聊
2. 点击右上角 **...** → **设置** → **群机器人** → **添加机器人**
3. 选择 **自定义机器人**
4. 复制 Webhook 地址

### 3. 启用 GitHub Actions

进入 **Actions** 标签页，点击 **I understand my workflows, go ahead and enable them**

### 4. 手动测试运行

点击左侧 **Reddit Monitor** → **Run workflow** → **Run workflow**

查看运行日志确认一切正常。

## 自定义配置

### 修改监控的 Subreddit

编辑 `config.py` 中的 `SUBREDDITS` 列表：

```python
SUBREDDITS = [
    "gamedev",
    "indiegaming", 
    "IndieDev",
    # 添加更多...
]
```

### 修改运行频率

编辑 `.github/workflows/monitor.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 * * * *'  # 每小时运行
  # - cron: '*/30 * * * *'  # 每30分钟运行
  # - cron: '0 */2 * * *'  # 每2小时运行
```

### 修改产品信息

编辑 `config.py` 中的产品配置：

```python
PRODUCT_NAME = "你的产品名"
PRODUCT_DESCRIPTION = "你的产品描述"
```

同时需要修改 `src/gemini_analyzer.py` 中的 `ANALYSIS_PROMPT` 以匹配你的目标用户。

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export GEMINI_API_KEY="your-api-key"
export FEISHU_WEBHOOK_URL="your-webhook-url"

# 运行
python src/main.py
```

## 文件结构

```
reddit监测/
├── .github/workflows/
│   └── monitor.yml      # GitHub Actions 配置
├── src/
│   ├── main.py              # 主入口
│   ├── reddit_fetcher.py    # Reddit RSS 抓取
│   ├── gemini_analyzer.py   # Gemini 分析模块
│   └── feishu_notifier.py   # 飞书通知模块
├── data/
│   └── processed_posts.json # 已处理帖子记录
├── config.py                # 配置文件
├── requirements.txt         # 依赖
└── README.md               
```

## 飞书卡片效果

收到的通知卡片包含：
- 📌 帖子标题
- 📝 内容预览
- 🤖 AI 判断理由
- 💬 参考回复（可直接复制使用）
- 🔗 一键跳转原帖按钮

## 注意事项

1. **GitHub Actions 免费额度**：每月 2000 分钟，每小时运行约消耗 1-2 分钟，足够使用
2. **Gemini API 免费额度**：每分钟 60 次请求，每天约 1500 次，足够使用
3. **避免被 Reddit 限制**：使用 RSS 而非 API，无需认证，更稳定
4. **去重机制**：已处理的帖子不会重复推送

## License

MIT
