def str_rule_get_str_idea(data: str) -> str | None:
    if not data.startswith("--"):
        return f"----\n{data.splitlines()[0]}\n"
    return None
