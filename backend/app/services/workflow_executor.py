from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog

from app.ai.streaming import sse
from app.models.workflow import Workflow
from app.services import tools_service

logger = structlog.get_logger()

MAX_STEPS = 20


async def execute_workflow(
    workflow: Workflow,
    message: str,
) -> AsyncGenerator[str, None]:
    """Execute a workflow DAG and yield SSE events."""
    try:
        definition = json.loads(workflow.definition)
    except (json.JSONDecodeError, TypeError):
        logger.error("workflow_invalid_definition", workflow_id=str(workflow.id))
        yield sse("chat.error", message="工作流定义格式错误")
        return

    nodes: dict[str, dict[str, Any]] = {n["id"]: n for n in definition.get("nodes", [])}
    current_id: str | None = definition.get("start")
    context: dict[str, str] = {"message": message}
    steps = 0

    while current_id and steps < MAX_STEPS:
        node = nodes.get(current_id)
        if not node:
            logger.error("workflow_node_missing", node_id=current_id)
            break

        node_type = node.get("type")
        data: dict[str, Any] = node.get("data", {})
        steps += 1

        if node_type == "end":
            break

        elif node_type == "send_message":
            text: str = data.get("text", "")
            if text:
                yield sse("chat.content_chunk", text=text)
            current_id = node.get("next")

        elif node_type == "condition":
            field = data.get("field", "message")
            operator = data.get("operator", "contains")
            value = str(data.get("value", ""))
            field_value = context.get(field, "").lower()
            matched = False
            if operator == "contains":
                matched = value.lower() in field_value
            elif operator == "equals":
                matched = field_value == value.lower()
            elif operator == "starts_with":
                matched = field_value.startswith(value.lower())
            current_id = node.get("next_true") if matched else node.get("next_false")

        elif node_type == "tool_call":
            tool_name: str = data.get("tool", "")
            tool_params: dict[str, Any] = data.get("params", {})
            # substitute {{message}} placeholder
            resolved_params = {
                k: v.replace("{{message}}", message) if isinstance(v, str) else v
                for k, v in tool_params.items()
            }
            if tool_name:
                yield sse("chat.tool_call", tool=tool_name)
                try:
                    result = await tools_service.execute_tool(tool_name, resolved_params)
                    context[f"tool_result_{tool_name}"] = json.dumps(
                        result, ensure_ascii=False
                    )
                    yield sse("chat.tool_result", tool=tool_name)
                except Exception as e:
                    logger.warning("workflow_tool_failed", tool=tool_name, error=str(e))
                    context[f"tool_result_{tool_name}"] = f"查询失败：{e}"
            current_id = node.get("next")

        else:
            logger.warning("workflow_unknown_node_type", node_type=node_type)
            current_id = node.get("next")
