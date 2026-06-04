# My Skill Project

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
| `miniprogram-prototype-designer` | 将需求文本整理成小程序 / H5 / 移动端原型、页面结构、流程和开发导向输出 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/My-Skill-Project --path miniprogram-prototype-designer` |
| `icon-generator` | 根据自然语言生成 SVG 图标，以及 React / Vue 图标组件 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/My-Skill-Project --path icon-generator` |
| `find-skills` | 帮助 Agent 发现、筛选并安装适合当前任务的新 skills | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/My-Skill-Project --path find-skills` |
| `codegraph-guide` | 指导 Codex 配置和使用 CodeGraph MCP 进行代码索引、调用链追踪和影响分析 | `python C:\Users\MSI\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo Fatelast/My-Skill-Project --path codegraph-guide` |

## 目录结构

```text
My-Skill-Project/
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
