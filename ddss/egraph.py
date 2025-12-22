from __future__ import annotations
import typing
from apyds import Term
from apyds_egg import EGraph as ApydsEGraph, EClassId
from .utility import (
    rule_is_fact,
    rule_get_fact,
    rule_is_equality,
    rule_get_equality,
    equality_build_rule,
    equality_build_term,
    term_build_rule,
)


class EGraph:
    def __init__(self):
        self.core = ApydsEGraph()
        self.mapping: dict[str, EClassId] = {}

    def _get_or_add(self, data: str) -> EClassId:
        if data not in self.mapping:
            self.mapping[data] = self.core.add(Term(data))
        return self.mapping[data]

    def set_equality(self, lhs: str, rhs: str) -> None:
        lhs_id = self._get_or_add(lhs)
        rhs_id = self._get_or_add(rhs)
        self.core.merge(lhs_id, rhs_id)

    def get_equality(self, lhs: str, rhs: str) -> bool:
        lhs_id = self._get_or_add(lhs)
        rhs_id = self._get_or_add(rhs)
        return self.core.find(lhs_id) == self.core.find(rhs_id)


class Search:
    def __init__(self) -> None:
        self.egraph = EGraph()
        self.terms = set()
        self.facts = set()
        self.pairs = set()

    def rebuild(self) -> None:
        self.egraph.core.rebuild()
        for lhs in self.terms:
            for rhs in self.terms:
                if self.egraph.get_equality(lhs, rhs):
                    equality = Term(equality_build_term(lhs, rhs))
                    self.pairs.add(equality)

    def add(self, data: str) -> None:
        self._add_expr(data)
        self._add_fact(data)

    def _add_expr(self, data: str) -> None:
        if not rule_is_equality(data):
            return
        lhs, rhs = rule_get_equality(data)
        self.terms.add(lhs)
        self.terms.add(rhs)
        self.egraph.set_equality(lhs, rhs)

    def _add_fact(self, data: str) -> None:
        if not rule_is_fact(data):
            return
        fact = rule_get_fact(data)
        self.terms.add(fact)
        self.facts.add(fact)

    def execute(self, data: str) -> typing.Iterator[str]:
        yield from self._execute_expr(data)
        yield from self._execute_fact(data)

    def _execute_expr(self, data: str) -> typing.Iterator[str]:
        if not rule_is_equality(data):
            return
        lhs, rhs = rule_get_equality(data)
        if self.egraph.get_equality(lhs, rhs):
            yield equality_build_rule(lhs, rhs)
        query = Term(rule_get_fact(data))
        for target in self.pairs:
            if unification := target @ query:
                result = target.ground(unification, scope="1")
                yield term_build_rule(result)

    def _execute_fact(self, data: str) -> typing.Iterator[str]:
        if not rule_is_fact(data):
            return
        idea = rule_get_fact(data)
        for fact in self.facts:
            if self.egraph.get_equality(idea, fact):
                yield data
        for fact in self.facts:
            query = Term(equality_build_term(idea, fact))
            for target in self.pairs:
                if unification := target @ query:
                    result = target.ground(unification, scope="1")
                    yield term_build_rule(result.term[2])
