# 🤝 贡献指南 / Contributing

感谢你为 **ReadmeLint** 贡献力量！本文件说明参与开发的规范与流程。

## 开发环境 / Development Setup

```bash
git clone https://github.com/gitstq/readmelint.git
cd readmelint
make dev        # 以可编辑模式安装（含测试依赖）
make test      # 运行单元测试
```

## 提交规范 / Commit Convention

请遵循 **Angular 提交规范**：

| 前缀       | 含义                         |
| ---------- | ---------------------------- |
| `feat:`    | 新增功能                     |
| `fix:`     | 修复问题                     |
| `docs:`    | 文档更新                     |
| `refactor:`| 代码重构（无功能变化）       |
| `test:`    | 测试相关                     |
| `chore:`   | 构建/工程化调整              |

示例：`feat: 新增 PDF 文档支持规则`

## 提交流程 / Workflow

1. Fork 本仓库并创建特性分支：`git checkout -b feat/your-feature`
2. 编写代码并补充/更新测试
3. 运行 `make test` 确保全部通过
4. 提交并推送，发起 Pull Request，清晰描述改动动机

## 规则扩展 / Adding Rules

规则集中在 `readmelint/rules.py` 的 `DEFAULT_RULES` 注册表中。新增规则只需实现一个
`check(doc, ctx) -> bool` 函数并登记 `Rule(...)`，无需改动评分与报告逻辑。

---

Thanks for contributing! Please open an issue or PR — all constructive input is welcome.
