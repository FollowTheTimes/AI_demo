import json


def parse_script(script):
    if isinstance(script, dict):
        return script
    if isinstance(script, str):
        try:
            return json.loads(script)
        except (json.JSONDecodeError, TypeError):
            return None
    return None
