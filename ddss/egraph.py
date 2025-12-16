from __future__ import annotations
import typing
import egglog
from apyds import Term, List
from .utility import (
    rule_is_fact,
    rule_get_fact,
    rule_is_equality,
    rule_get_equality,
    equality_build_rule,
    equality_build_term,
    term_build_rule,
)


class EGraphTerm(egglog.Expr):
    def __init__(self, name: egglog.StringLike) -> None: ...

    @classmethod
    def begin(cls) -> EGraphTerm: ...

    @classmethod
    def pair(cls, lhs: EGraphTerm, rhs: EGraphTerm) -> EGraphTerm: ...


class Search:
    def __init__(self) -> None:
        self.egraph = egglog.EGraph()
        self.terms = set()
        self.facts = set()
        self.pairs = set()

    def build_pairs(self) -> None:
        for lhs in self.terms:
            for rhs in self.terms:
                if self._get_equality(lhs, rhs):
                    equality = Term(equality_build_term(lhs, rhs))
                    self.pairs.add(equality)

    def _ast_from_term(self, data: Term) -> EGraphTerm:
        term = data.term
        if isinstance(term, List):
            result = EGraphTerm.begin()
            for i in range(len(term)):
                child = self._ast_from_term(term[i])
                result = EGraphTerm.pair(result, child)
            return result
        else:
            return EGraphTerm(str(term))

    def _ast(self, data: str) -> EGraphTerm:
        result = self._ast_from_term(Term(data))
        self.egraph.register(result)
        return result

    def _set_equality(self, lhs: str, rhs: str) -> None:
        self.egraph.register(egglog.union(self._ast(lhs)).with_(self._ast(rhs)))

    def _get_equality(self, lhs: str, rhs: str) -> None:
        return self.egraph.check_bool(self._ast(lhs) == self._ast(rhs))

    def add(self, data: str) -> None:
        self._add_expr(data)
        self._add_fact(data)

    def _add_expr(self, data: str) -> None:
        if not rule_is_equality(data):
            return
        lhs, rhs = rule_get_equality(data)
        self.terms.add(lhs)
        self.terms.add(rhs)
        self._set_equality(lhs, rhs)

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
        if self._get_equality(lhs, rhs):
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
            if self._get_equality(idea, fact):
                yield data
        for fact in self.facts:
            query = Term(equality_build_term(idea, fact))
            for target in self.pairs:
                if unification := target @ query:
                    result = target.ground(unification, scope="1")
                    yield term_build_rule(result.term[2])
