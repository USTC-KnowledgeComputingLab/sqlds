from apyds import Rule


def rule_get_idea(data):
    if not data.startswith("--"):
        return f"----\n{data.splitlines()[0]}\n"
    return None


def rule_is_fact(data):
    return data.startswith("--")


def rule_get_fact(data):
    return data.splitlines()[-1]


def rule_is_equality(data):
    return data.startswith("----\n(binary == ")


def rule_get_equality(data):
    term = Rule(data).conclusion
    lhs = str(term.term[2])
    rhs = str(term.term[3])
    return lhs, rhs


def build_equality_rule(lhs: str, rhs: str) -> str:
    return f"----\n(binary == {lhs} {rhs})\n"
