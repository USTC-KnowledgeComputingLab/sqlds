from __future__ import annotations
import typing
from apyds import Term, Rule, List
from apyds_egg import EGraph, EClassId


def _build_term_to_rule(data: Term) -> Rule:
    return Rule(f"----\n{data}\n")


def _extract_lhs_rhs_from_rule(data: Rule) -> tuple[Term, Term] | None:
    if len(data) != 0:
        return
    term = data.conclusion.term
    if not isinstance(term, List):
        return
    if not (len(term) == 4 or str(term[0]) == "binary" or str(term[1]) == "=="):
        return
    lhs = term[2]
    rhs = term[3]
    return lhs, rhs


def _build_lhs_rhs_to_term(lhs: Term, rhs: Term) -> Term:
    return Term(f"(binary == {lhs} {rhs})")


class _EGraph:
    def __init__(self):
        self.core = EGraph()
        self.mapping: dict[Term, EClassId] = {}

    def _get_or_add(self, data: Term) -> EClassId:
        if data not in self.mapping:
            self.mapping[data] = self.core.add(data)
        return self.mapping[data]

    def set_equality(self, lhs: Term, rhs: Term) -> None:
        lhs_id = self._get_or_add(lhs)
        rhs_id = self._get_or_add(rhs)
        self.core.merge(lhs_id, rhs_id)

    def get_equality(self, lhs: Term, rhs: Term) -> bool:
        lhs_id = self._get_or_add(lhs)
        rhs_id = self._get_or_add(rhs)
        return self.core.find(lhs_id) == self.core.find(rhs_id)

    def rebuild(self) -> None:
        self.core.rebuild()


class Search:
    def __init__(self) -> None:
        self.egraph: _EGraph = _EGraph()
        self.terms: set[Term] = set()
        self.facts: set[Term] = set()
        self.pairs: set[Term] = set()

    def rebuild(self) -> None:
        self.egraph.rebuild()
        for lhs in self.terms:
            for rhs in self.terms:
                if self.egraph.get_equality(lhs, rhs):
                    equality = _build_lhs_rhs_to_term(lhs, rhs)
                    self.pairs.add(equality)

    def add(self, data: Rule) -> None:
        self._add_expr(data)
        self._add_fact(data)

    def _add_expr(self, data: Rule) -> None:
        lhs_rhs = _extract_lhs_rhs_from_rule(data)
        if lhs_rhs is None:
            return
        lhs, rhs = lhs_rhs
        self.terms.add(lhs)
        self.terms.add(rhs)
        self.egraph.set_equality(lhs, rhs)

    def _add_fact(self, data: Rule) -> None:
        if len(data) != 0:
            return
        term = data.conclusion
        self.terms.add(term)
        self.facts.add(term)

    def execute(self, data: Rule) -> typing.Iterator[Rule]:
        yield from self._execute_expr(data)
        yield from self._execute_fact(data)

    def _execute_expr(self, data: Rule) -> typing.Iterator[Rule]:
        lhs_rhs = _extract_lhs_rhs_from_rule(data)
        if lhs_rhs is None:
            return
        lhs, rhs = lhs_rhs
        # 检查是否已经存在严格相等的事实
        if self.egraph.get_equality(lhs, rhs):
            yield data
        # 尝试处理含有变量的情况
        query = data.conclusion
        for target in self.pairs:
            if unification := target @ query:
                if result := target.ground(unification, scope="1"):
                    yield _build_term_to_rule(result)

    def _execute_fact(self, data: Rule) -> typing.Iterator[Rule]:
        if len(data) != 0:
            return
        idea = data.conclusion
        # 检查是否已经存在严格相等的事实
        for fact in self.facts:
            if self.egraph.get_equality(idea, fact):
                yield data
        # 尝试处理含有变量的情况
        for fact in self.facts:
            query = _build_lhs_rhs_to_term(idea, fact)
            for target in self.pairs:
                if unification := target @ query:
                    if result := target.ground(unification, scope="1"):
                        term = result.term
                        if isinstance(term, List):
                            yield _build_term_to_rule(term[2])
