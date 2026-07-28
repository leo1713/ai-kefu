import json


def sse(event: str, **data: object) -> str:
    payload = json.dumps({"event": event, **data}, ensure_ascii=False)
    return f"data: {payload}\n\n"
