#!/bin/bash
# init.sh — 会话启动脚本
# 每次新会话开始前运行此脚本，验证环境健康，再开始写代码。
# 用法：bash init.sh

set -e

echo ""
echo "======================================"
echo "  ai-cs 会话初始化检查"
echo "======================================"
echo ""

PASS=0
FAIL=0

check() {
    local desc="$1"
    local cmd="$2"
    printf "%-50s" "  $desc ..."
    if eval "$cmd" > /dev/null 2>&1; then
        echo " ✓"
        PASS=$((PASS + 1))
    else
        echo " ✗  (运行 '$cmd' 失败)"
        FAIL=$((FAIL + 1))
    fi
}

# ── 工具链检查 ────────────────────────────────────────────────
echo "[ 工具链 ]"
check "Docker"          "docker info"
check "Docker Compose"  "docker compose version"
check "Python 3.11+"    "python3 -c 'import sys; assert sys.version_info >= (3,11)'"
check "Poetry"          "poetry --version"
check "Node.js 22+"     "node -e 'process.exit(parseInt(process.version.slice(1)) >= 22 ? 0 : 1)'"
check "Make"            "make --version"
echo ""

# ── 环境文件检查 ──────────────────────────────────────────────
echo "[ 环境配置 ]"
if [ -f .env ]; then
    echo "  .env 文件存在                                       ✓"
    PASS=$((PASS + 1))
else
    echo "  .env 文件不存在                                     ✗  (从 .env.example 复制并填写)"
    FAIL=$((FAIL + 1))
fi
echo ""

# ── 项目代码检查（仅在代码已存在时运行）─────────────────────
if [ -f "backend/pyproject.toml" ]; then
    echo "[ 后端代码检查 ]"
    check "Python 依赖已安装"   "cd backend && poetry check --quiet"
    check "ruff 规范检查"       "cd backend && poetry run ruff check . --quiet"
    check "mypy 类型检查"       "cd backend && poetry run mypy --strict app/ --quiet"
    check "pytest 单元测试"     "cd backend && poetry run pytest tests/unit/ -q --tb=no"
    echo ""
fi

if [ -f "frontend/admin/package.json" ]; then
    echo "[ 前端代码检查 ]"
    check "Node 依赖已安装"     "[ -d frontend/admin/node_modules ]"
    check "TypeScript 编译"     "cd frontend/admin && npx tsc --noEmit"
    check "ESLint 检查"         "cd frontend/admin && npx eslint . --quiet"
    echo ""
fi

# ── 进度文件检查 ──────────────────────────────────────────────
echo "[ Harness 文件 ]"
for f in AGENTS.md STATE.md architecture.md; do
    check "$f 存在" "[ -f $f ]"
done
echo ""

# ── 汇总 ──────────────────────────────────────────────────────
echo "======================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  ✅ 全部通过（$PASS 项）— 可以开始工作"
    echo ""
    echo "  下一步："
    echo "    读 STATE.md 的「上次会话记录 → 下一步行动」"
    echo "    从第一条任务开始，不要重新规划已完成的工作"
else
    echo "  ❌ $FAIL 项未通过，$PASS 项通过"
    echo ""
    echo "  请先修复上方 ✗ 项，再开始写代码。"
    echo "  环境不健康时写的代码很可能在 CI 里失败。"
fi
echo "======================================"
echo ""

exit "$FAIL"
