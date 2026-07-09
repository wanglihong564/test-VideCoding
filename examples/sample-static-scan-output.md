# 静态扫描输出示例

Root: `C:\projects\shop-api`
Files scanned: 148

## 项目清单文件

- `package.json`: `package.json`
- `package-lock.json`: `package-lock.json`
- `Dockerfile`: `Dockerfile`

## 包管理提示

- JavaScript 锁文件存在：package-lock.json

## Package Scripts

- `package.json` scripts: build, lint, test, test:e2e

## 检测到的框架

- Express/Fastify-style routing
- Next.js API Routes

## 路由清单

| 方法 | 路径 | 框架 | 文件 | 风险提示 |
|---|---|---|---|---|
| POST | `/api/orders` | Express/Fastify-style routing | `src/routes/orders.ts:18` | money(strong:path), data(medium:handler) |
| POST | `/api/webhooks/payment` | Express/Fastify-style routing | `src/routes/webhooks.ts:11` | money(strong:path) |
| PATCH | `/api/admin/users/:id` | Express/Fastify-style routing | `src/routes/admin.ts:28` | permissions(strong:path), data(strong:method) |

## 路由候选文件

- `src/routes/orders.ts`
- `src/routes/webhooks.ts`
- `src/routes/admin.ts`

## 测试候选文件

- `tests/orders.spec.ts`
- `tests/admin.spec.ts`

## 配置候选文件

- env_examples: `.env.example`
- ci: `.github/workflows/ci.yml`
- docker: `Dockerfile`
- migrations: `migrations/202607090001_create_orders.sql`

## 安全面

安全/认证相关文件：

- `src/middleware/auth.ts`
- `src/security/cors.ts`

高风险路由提示：

- `POST /api/orders` 位于 `src/routes/orders.ts:18`（money(strong:path)）
- `PATCH /api/admin/users/:id` 位于 `src/routes/admin.ts:28`（permissions(strong:path), data(strong:method)）

安全提示：

- 检测到权限敏感路由；需要验证水平越权和垂直越权。
- 检测到资金/订单/支付路由；需要验证后端金额可信、幂等性和 Webhook 签名。

## 测试质量警告

- `tests/admin.spec.ts`：只断言 HTTP 状态码，可能没有验证真实业务结果。

## 潜在密钥命中

- 启发式扫描未发现。

## 建议的安全命令

- `npm run build`
- `npm run lint`
- `npm run test`
- `npm run test:e2e`
- `npm audit`

## 建议的下一步检查

- 审查路由清单中的认证、授权、输入校验和敏感响应字段。
- 优先测试带有资金、权限、数据或可用性风险提示的路由。
- 检测到弱测试模式；验证重要测试是否断言真实业务结果。
- 审查迁移的备份、回滚、幂等性和旧数据兼容性。

