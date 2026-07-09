# Prelaunch Test Audit Skill

一个可复用的 Agent Skill，用于上线前发布就绪测试。

它可以帮助 Codex、Claude Code 和其他 AI coding agents 在项目上线前做结构化审计，重点关注：

- 功能正确性
- 权限与访问控制风险
- 数据安全
- 安全审查
- 回归测试
- 部署准备度
- 回滚安全
- 依赖与供应链风险
- `Go` / `Conditional Go` / `No Go` 上线决策

## 为什么需要它

AI coding agents 很擅长构建功能，但它们在修复某一个具体任务时，也可能不小心破坏已有流程。

这个 skill 给 Agent 一套标准化的上线前审计流程：

- 从只读审计模式开始
- 识别高风险区域
- 设计正常、边界、异常和滥用场景测试
- 检查测试是真的验证业务结果，还是只验证了表面状态
- 审查安全、部署、回滚和供应链风险
- 输出最终的 `Go` / `Conditional Go` / `No Go` 决策

## 安装

### Codex

把 skill 文件夹复制到：

```text
<your-project>/.agents/skills/prelaunch-test-audit/
```

调用：

```text
Use $prelaunch-test-audit in read-only audit mode. Do not modify code.
```

### Claude Code

把 skill 文件夹复制到：

```text
<your-project>/.claude/skills/prelaunch-test-audit/
```

调用：

```text
/prelaunch-test-audit
```

或者：

```text
Use the prelaunch-test-audit skill. Start with read-only audit. Do not modify code.
```

## 仓库结构

真正需要复制和安装的是这个目录：

```text
prelaunch-test-audit/
  SKILL.md
  agents/openai.yaml
  assets/templates/
  references/test-prompts.md
  scripts/prelaunch_static_scan.py
```

仓库根目录里的 `README.md`、`LICENSE` 和 `examples/` 是给人看的说明和示例，不需要复制进 Agent skills 目录。

## 只读静态扫描

Skill 内置了一个只读脚本：

```bash
python prelaunch-test-audit/scripts/prelaunch_static_scan.py <project-root>
```

它会扫描：

- 项目 manifest 和 lockfile
- package scripts
- 常见框架和路由
- 安全相关文件
- 潜在弱测试模式
- 潜在密钥类字符串
- 建议执行的安全命令

这个脚本不会运行测试、不会执行依赖审计、不会发起安全探测，也不会修改项目文件。

## 示例

可以参考：

- `examples/sample-audit-report.md`
- `examples/sample-go-no-go-report.md`
- `examples/sample-static-scan-output.md`

## 安全边界

这个 Skill 默认以只读审计为主。动态安全测试默认只应在本地或测试环境执行；如果目标是生产环境，只做低风险验证，除非用户明确授权具体测试范围。
