from __future__ import annotations

ROUTE_TO_AGENT_TOOL: dict[str, object] = {
    "name": "route_to_agent",
    "description": (
        "将用户请求路由给对应的专业客服 Agent 处理。\n"
        "当用户的问题属于以下情形时调用：\n"
        "- 涉及退款、退货、赔偿 → 选择 refund\n"
        "- 涉及快递、物流、包裹查询 → 选择 logistics\n"
        "直接调用此工具即可，不要先自行回答。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": ["refund", "logistics"],
                "description": "目标专业 Agent：refund（退款专员）或 logistics（物流专员）",
            },
            "reason": {
                "type": "string",
                "description": "路由原因（简要说明）",
            },
        },
        "required": ["agent", "reason"],
    },
}
ROUTE_TO_AGENT_TOOL_NAME = "route_to_agent"
