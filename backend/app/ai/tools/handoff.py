"""
handoff 工具：AI 主动触发转人工。

当 AI 判断需要转接人工客服时，调用此工具。
chat_service 检测到此工具调用后，将会话 status 改为 transferred。
"""
from __future__ import annotations

# Claude tool definition（JSON Schema 格式，直接传给 Anthropic API）
HANDOFF_TOOL: dict[str, object] = {
    "name": "transfer_to_human",
    "description": (
        "当遇到以下情况时调用此工具，将对话转接给人工客服：\n"
        "1. 用户明确要求转人工\n"
        "2. 问题超出知识库范围且无法有效回答\n"
        "3. 用户情绪激动，需要人工安抚\n"
        "4. 涉及退款、赔偿等需要人工授权的操作\n"
        "5. 连续3次无法解答用户问题\n\n"
        "调用后对话将立即转接，请在 reason 中简要说明转接原因。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "转人工的原因，简洁说明（例如：用户要求退款，需要人工审批）",
            },
            "summary": {
                "type": "string",
                "description": "对话摘要，帮助客服快速了解上下文（100字以内）",
            },
        },
        "required": ["reason", "summary"],
    },
}

HANDOFF_TOOL_NAME = "transfer_to_human"
