#!/bin/bash
# check-arch.sh — 架构约束可执行检查
# 对应 AGENTS.md 中的硬约束，违反任一条退出码非0
# 用法：bash scripts/check-arch.sh
# 在 make check 中调用

set -e
ERRORS=0
BACKEND_DIR="backend/app"

# 如果后端代码目录不存在，跳过（Sprint 1.1 之前正常）
if [ ! -d "$BACKEND_DIR" ]; then
  echo "⚠️  $BACKEND_DIR 不存在，跳过架构检查（代码尚未创建）"
  exit 0
fi

echo "=== 架构约束检查 ==="

# ---------------------------------------------------------------
# 约束1：路由层不直接操作数据库
# 路由文件（app/api/）中不应出现 db.execute / select( / session.
# ---------------------------------------------------------------
echo "检查 [约束1] 路由层不直接操作数据库..."
VIOLATIONS=$(grep -rn \
  -e "db\.execute\|await db\|session\.execute\|select(" \
  --include="*.py" \
  "$BACKEND_DIR/api/" 2>/dev/null || true)
if [ -n "$VIOLATIONS" ]; then
  echo "❌ [约束1] 路由层直接操作数据库："
  echo "$VIOLATIONS"
  echo "   FIX: 将数据库操作移到 app/services/ 对应的 service 文件中"
  ERRORS=$((ERRORS + 1))
else
  echo "   ✅ 通过"
fi

# ---------------------------------------------------------------
# 约束2：禁止使用 SQLAlchemy 1.x 的 db.query() 风格
# ---------------------------------------------------------------
echo "检查 [约束2] 禁止 SQLAlchemy 1.x db.query() 风格..."
VIOLATIONS=$(grep -rn "\.query(" --include="*.py" "$BACKEND_DIR/" 2>/dev/null || true)
if [ -n "$VIOLATIONS" ]; then
  echo "❌ [约束2] 使用了 SQLAlchemy 1.x 的 .query() 风格："
  echo "$VIOLATIONS"
  echo "   FIX: 改用 SQLAlchemy 2.0 语法: select(Model).where(...)"
  ERRORS=$((ERRORS + 1))
else
  echo "   ✅ 通过"
fi

# ---------------------------------------------------------------
# 约束3：禁止使用 print()，必须用 structlog
# ---------------------------------------------------------------
echo "检查 [约束3] 禁止使用 print()..."
VIOLATIONS=$(grep -rn "^\s*print(" --include="*.py" "$BACKEND_DIR/" 2>/dev/null || true)
if [ -n "$VIOLATIONS" ]; then
  echo "❌ [约束3] 使用了 print()："
  echo "$VIOLATIONS"
  echo "   FIX: 改用 from app.core.logging import logger，然后 logger.info(...)"
  ERRORS=$((ERRORS + 1))
else
  echo "   ✅ 通过"
fi

# ---------------------------------------------------------------
# 约束4：Service 层不直接返回 HTTP 响应（不 import fastapi Response/HTTPException）
# ---------------------------------------------------------------
echo "检查 [约束4] Service 层不返回 HTTP 响应..."
VIOLATIONS=$(grep -rn \
  -e "from fastapi import.*HTTPException\|from fastapi.responses import\|JSONResponse\|HTMLResponse" \
  --include="*.py" \
  "$BACKEND_DIR/services/" 2>/dev/null || true)
if [ -n "$VIOLATIONS" ]; then
  echo "❌ [约束4] Service 层直接使用了 HTTP 响应类型："
  echo "$VIOLATIONS"
  echo "   FIX: Service 层抛出 AppException，在路由层捕获并转换为 HTTP 响应"
  ERRORS=$((ERRORS + 1))
else
  echo "   ✅ 通过"
fi

# ---------------------------------------------------------------
# 约束5：外部 HTTP 调用必须设置 timeout
# （httpx 调用时必须有 timeout= 参数）
# ---------------------------------------------------------------
echo "检查 [约束5] 外部 HTTP 调用必须设置 timeout..."
# 找到所有用 httpx 发请求但没有 timeout= 的行
VIOLATIONS=$(grep -rn "httpx\.\(get\|post\|put\|delete\|patch\|request\)(" \
  --include="*.py" "$BACKEND_DIR/" 2>/dev/null \
  | grep -v "timeout=" || true)
if [ -n "$VIOLATIONS" ]; then
  echo "❌ [约束5] httpx 调用缺少 timeout= 参数："
  echo "$VIOLATIONS"
  echo "   FIX: 添加 timeout=10.0，例如 httpx.get(url, timeout=10.0)"
  ERRORS=$((ERRORS + 1))
else
  echo "   ✅ 通过"
fi

# ---------------------------------------------------------------
# 约束6：Schema 层不 import Model 层
# ---------------------------------------------------------------
echo "检查 [约束6] Schema 层不导入 Model 层..."
VIOLATIONS=$(grep -rn "from app\.models\|import app\.models" \
  --include="*.py" "$BACKEND_DIR/schemas/" 2>/dev/null || true)
if [ -n "$VIOLATIONS" ]; then
  echo "❌ [约束6] Schema 层导入了 Model 层："
  echo "$VIOLATIONS"
  echo "   FIX: Schema 不依赖 Model。转换逻辑放在 service 层或用 model_validate()"
  ERRORS=$((ERRORS + 1))
else
  echo "   ✅ 通过"
fi

# ---------------------------------------------------------------
# 约束7：前端组件不直接写 fetch（必须通过 src/api/ 封装）
# ---------------------------------------------------------------
FRONTEND_DIR="frontend/admin/src"
if [ -d "$FRONTEND_DIR" ]; then
  echo "检查 [约束7] 前端组件不直接使用 fetch/axios..."
  VIOLATIONS=$(grep -rn \
    -e "\bfetch(" \
    -e "axios\." \
    --include="*.tsx" --include="*.ts" \
    "$FRONTEND_DIR/components/" "$FRONTEND_DIR/pages/" 2>/dev/null \
    | grep -v "src/api/" || true)
  if [ -n "$VIOLATIONS" ]; then
    echo "❌ [约束7] 前端组件直接调用 fetch/axios："
    echo "$VIOLATIONS"
    echo "   FIX: 将 API 调用封装到 src/api/ 目录下的函数，组件只调用封装函数"
    ERRORS=$((ERRORS + 1))
  else
    echo "   ✅ 通过"
  fi
else
  echo "⚠️  $FRONTEND_DIR 不存在，跳过前端架构检查"
fi

# ---------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------
echo ""
if [ $ERRORS -eq 0 ]; then
  echo "=== 架构约束检查全部通过 ✓ ==="
  exit 0
else
  echo "=== 架构约束检查发现 $ERRORS 个违规 ✗ ==="
  echo "请按照上方 FIX 提示修复后重新运行"
  exit 1
fi
