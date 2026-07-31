from __future__ import annotations

ORDER_QUERY_TOOL: dict[str, object] = {
    "name": "query_order",
    "description": (
        "查询订单信息，包括订单状态、商品明细、金额、创建时间等。"
        "当用户提供订单号并询问订单相关信息时调用。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "订单号，例如 '20240728001'",
            },
        },
        "required": ["order_id"],
    },
}
ORDER_QUERY_TOOL_NAME = "query_order"

PAYMENT_QUERY_TOOL: dict[str, object] = {
    "name": "query_payment",
    "description": (
        "查询支付记录，包括支付状态、支付金额、支付时间、支付方式等。"
        "当用户询问是否付款成功或退款状态时调用。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "订单号",
            },
        },
        "required": ["order_id"],
    },
}
PAYMENT_QUERY_TOOL_NAME = "query_payment"

LOGISTICS_QUERY_TOOL: dict[str, object] = {
    "name": "query_logistics",
    "description": (
        "查询物流/快递信息，包括快递公司、运单号、当前位置、预计到达时间。"
        "当用户询问包裹/快递进展时调用。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "订单号（优先使用）",
            },
            "tracking_no": {
                "type": "string",
                "description": "快递单号（order_id 未知时使用）",
            },
        },
        "required": [],
    },
}
LOGISTICS_QUERY_TOOL_NAME = "query_logistics"
