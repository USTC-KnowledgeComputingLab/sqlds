from apyds import Term


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
    return term_get_equality(rule_get_fact(data))


def term_get_equality(data):
    term = Term(data)
    lhs = str(term.term[2])
    rhs = str(term.term[3])
    return lhs, rhs


def equality_build_rule(lhs: str, rhs: str) -> str:
    return term_build_rule(equality_build_term(lhs, rhs))


def equality_build_term(lhs: str, rhs: str) -> str:
    return f"(binary == {lhs} {rhs})"


def term_build_rule(data: str) -> str:
    return f"----\n{data}\n"
