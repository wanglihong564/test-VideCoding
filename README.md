# Prelaunch Test Audit Skill

这是一个可复用的 Codex Skill，用于上线前测试、发布前审计、回归测试规划、安全检查和 Go/No-Go 上线决策。

它的重点不是“把所有地方都测一遍”，而是优先发现真正会影响上线的风险：资金、权限、数据、可用性、安全、回滚、监控和第三方集成。

## 怎么安装

克隆这个仓库后，把 `prelaunch-test-audit/` 目录复制到你的 Codex skills 目录即可。

Windows PowerShell：

```powershell
Copy-Item -Recurse .\prelaunch-test-audit "$env:USERPROFILE\.agents\skills\prelaunch-test-audit"
```

macOS / Linux：

```bash
cp -R prelaunch-test-audit ~/.agents/skills/prelaunch-test-audit
```

复制完成后，重启 Codex，或按你的环境方式重新加载 skills。

## 怎么使用

在 Codex 里可以这样说：

```text
Use $prelaunch-test-audit in read-only audit mode to check whether this project is ready to launch.
```

也可以用这些提示词：

```text
Use $prelaunch-test-audit to run a Go/No-Go launch review for this repo.
```

```text
Use $prelaunch-test-audit to identify high-risk routes, weak tests, missing rollback checks, and launch blockers.
```

```text
Use $prelaunch-test-audit to design regression tests for the payment, permission, and data-write flows.
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

仓库根目录里的 `README.md`、`LICENSE` 和 `examples/` 是给人看的说明和示例，不需要复制进 Codex skills 目录。

## 这个 Skill 能做什么

- 判断项目是否适合上线，并输出 `Go`、`Conditional Go` 或 `No Go`
- 识别支付、订单、权限、数据写入、上传、导出、Webhook 等高风险路径
- 检查测试是否只验证了 HTTP 200 或 `success: true`，而没有验证真实业务结果
- 生成上线前审计报告、问题报告、回归测试设计和 Go/No-Go 决策
- 检查环境变量、密钥、依赖锁文件、部署配置、回滚、监控和第三方集成
- 使用只读静态扫描脚本辅助快速盘点项目结构

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
