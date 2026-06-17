# LFs Skills

一个用于存放个人 Codex skills 的仓库。

当前仓库只承担一件事：按 skill 目录组织可独立安装的能力包。每个 skill 保持自包含，按需携带 `SKILL.md`、`agents/`、`references/`、`scripts/` 等文件。

## 仓库定位

- 这是一个多 skill 集合仓库，不是单一项目仓库
- 每个 skill 都应放在自己的独立目录中
- 每个 skill 都应可以单独安装、单独维护
- 根目录 README 只负责索引和说明，不承载某个 skill 的详细文档

## 当前 Skills

| Skill | 用途 | 安装命令 |
|---|---|---|
| `miniprogram-prototype-designer` | 将需求文本整理成小程序 / H5 / 移动端原型、页面结构、流程和开发导向输出 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path miniprogram-prototype-designer` |
| `icon-generator` | 根据自然语言生成 SVG 图标，以及 React / Vue 图标组件 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path icon-generator` |
| `find-skills` | 帮助 Agent 发现、筛选并安装适合当前任务的新 skills | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path find-skills` |
| `codegraph-guide` | 指导 Codex 配置和使用 CodeGraph MCP 进行代码索引、调用链追踪和影响分析 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path codegraph-guide` |
| `project-context-manager` | 管理跨会话项目上下文文档，帮助 Codex 维护 AGENTS.md 和 docs/codex 交接资料 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path project-context-manager` |
| `skill-optimizer` | 审查并优化现有 skill 的触发语义、工作流、确认门槛、资源组织、安全边界与文档分层 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path skill-optimizer` |
| `stock-short-term-analysis` | 结合数据可信度、市场情绪、板块强弱、参与者结构、财报公告和技术量价，分析 A 股短线机会与风险 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path stock-short-term-analysis` |
| `premarket-trend-frontline-stock-selection` | 根据 A 股盘前行情、板块强弱、公告财报、资金参与者线索和竞价条件，筛选短线观察池并制定盘中确认条件 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path premarket-trend-frontline-stock-selection` |
| `gsap-core` | 使用 GSAP 核心 API 编写基础 tween、缓动、stagger、响应式和 reduced-motion 动画 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-core` |
| `gsap-timeline` | 编排多步骤动画、时间线、label、嵌套 timeline 和播放控制 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-timeline` |
| `gsap-scrolltrigger` | 实现 ScrollTrigger 滚动触发、pin、scrub、视差和横向滚动动画 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-scrolltrigger` |
| `gsap-plugins` | 使用 GSAP 插件，如 Flip、Draggable、SplitText、MorphSVG、DrawSVG、ScrollTo 和 MotionPath | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-plugins` |
| `gsap-utils` | 使用 gsap.utils 进行 clamp、mapRange、normalize、random、snap、toArray、wrap 等辅助处理 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-utils` |
| `gsap-react` | 在 React / Next.js 中使用 GSAP，处理 useGSAP、refs、作用域和卸载清理 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-react` |
| `gsap-performance` | 优化 GSAP 动画性能，减少卡顿、布局抖动和不必要的重绘 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-performance` |
| `gsap-frameworks` | 在 Vue、Nuxt、Svelte、SvelteKit 等非 React 框架中使用 GSAP 并处理生命周期清理 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/LFs-skills --path gsap-skills/gsap-frameworks` |

## 目录结构

```text
LFs-skills/
  README.md
  miniprogram-prototype-designer/
    SKILL.md
    agents/
      openai.yaml
    references/
      html-prototype-guidelines.md
      prototype-output-template.md
  icon-generator/
    SKILL.md
    agents/
      openai.yaml
    scripts/
      icon_transform.py
  find-skills/
    SKILL.md
  codegraph-guide/
    SKILL.md
    agents/
      openai.yaml
  project-context-manager/
    SKILL.md
    agents/
      openai.yaml
  skill-optimizer/
    README.md
    SKILL.md
    references/
      review-checklist.md
      skill-creation-best-practices-claude-api-docs.md
      skill-design-review-framework.md
  stock-short-term-analysis/
    SKILL.md
  premarket-trend-frontline-stock-selection/
    SKILL.md
  gsap-skills/
    gsap-core/
      SKILL.md
    gsap-frameworks/
      SKILL.md
    gsap-performance/
      SKILL.md
    gsap-plugins/
      SKILL.md
    gsap-react/
      SKILL.md
    gsap-scrolltrigger/
      SKILL.md
    gsap-timeline/
      SKILL.md
    gsap-utils/
      SKILL.md
```

## 使用方式

1. 选择需要的 skill
2. 使用 `skill-installer` 按目录路径安装
3. 重启 Codex 以加载新 skill
4. 在对话中通过 skill 名称触发，例如：`$icon-generator`

## 每个 Skill 的最小约定

建议每个 skill 目录遵循下面的最小结构：

- `SKILL.md`：必需，定义 skill 名称、触发描述和工作规则
- `agents/openai.yaml`：推荐，提供 UI 展示名称和简短说明
- `references/`：可选，放按需读取的参考文档
- `scripts/`：可选，放可复用脚本或辅助工具

## 维护原则

- 保持 skill 目录自包含，不把某个 skill 的说明混到根 README
- 根 README 只维护仓库级信息、skill 列表和安装入口
- 新增 skill 时优先复用现有结构，不为仓库引入额外复杂层级
- 没有明确收益时，不新增 README 之外的仓库级辅助文档

## 后续新增 Skill 的建议

新增 skill 时，直接在仓库根目录下创建新的同名目录，例如：

```text
new-skill/
  SKILL.md
  agents/
    openai.yaml
```

然后在根 `README.md` 的 Skills 表格中补一行安装入口即可。

