from __future__ import annotations
import typing
import egglog
from apyds import Term, List
from .poly import Poly


class EGraphTerm(egglog.Expr):
    def __init__(self, name: egglog.StringLike) -> None: ...

    @classmethod
    def begin(cls) -> EGraphTerm: ...

    @classmethod
    def pair(cls, lhs: EGraphTerm, rhs: EGraphTerm) -> EGraphTerm: ...


def _ds_to_egraph(data: Term) -> EGraphTerm:
    term = data.term
    if isinstance(term, List):
        result = EGraphTerm.begin()
        for i in range(len(term)):
            child = _ds_to_egraph(term[i])
            result = EGraphTerm.pair(result, child)
        return result
    else:
        return EGraphTerm(str(term))


class Search:
    def __init__(self) -> None:
        self.egraph = egglog.EGraph()
        self.terms = set()
        self.facts = set()

    def _is_equality(self, data: Poly) -> bool:
        return data.ds.startswith("----\n(binary == ")

    def _extract_lhs_rhs(self, data: Poly) -> tuple[str, str]:
        term = data.rule.conclusion
        lhs = str(term.term[2])
        rhs = str(term.term[3])
        return lhs, rhs

    def _ast(self, data: str) -> EGraphTerm:
        result = _ds_to_egraph(Term(data))
        self.egraph.register(result)
        return result

    def _set_equality(self, lhs: str, rhs: str) -> None:
        self.egraph.register(egglog.union(self._ast(lhs)).with_(self._ast(rhs)))

    def _get_equality(self, lhs: str, rhs: str) -> None:
        return self.egraph.check_bool(self._ast(lhs) == self._ast(rhs))

    def _search_equality(self, data: str) -> typing.Iterator[str]:
        for result in self.terms:
            if self._get_equality(data, result):
                yield result

    def _build_equality(self, lhs: str, rhs: str) -> Poly:
        return Poly(ds=f"----\n(binary == {lhs} {rhs})")

    def add(self, data: Poly) -> None:
        self._add_expr(data)
        self._add_fact(data)

    def _add_expr(self, data: Poly) -> None:
        if not self._is_equality(data):
            return
        lhs, rhs = self._extract_lhs_rhs(data)
        self.terms.add(lhs)
        self.terms.add(rhs)
        self._set_equality(lhs, rhs)

    def _add_fact(self, data: Poly) -> None:
        if len(data.rule) != 0:
            return 0
        fact = str(data.rule.conclusion)
        self.terms.add(fact)
        self.facts.add(fact)

    def execute(self, data: Poly) -> typing.Iterator[Poly]:
        yield from self._execute_expr(data)
        yield from self._execute_fact(data)

    def _execute_expr(self, data: Poly) -> typing.Iterator[Poly]:
        if not self._is_equality(data):
            return
        lhs, rhs = self._extract_lhs_rhs(data)
        if self._get_equality(lhs, rhs):
            yield self._build_equality(lhs, rhs)
            return
        if lhs.startswith("`"):
            for result in self._search_equality(rhs):
                yield self._build_equality(result, rhs)
        if rhs.startswith("`"):
            for result in self._search_equality(lhs):
                yield self._build_equality(lhs, result)

    def _execute_fact(self, data: Poly) -> typing.Iterator[Poly]:
        if len(data.rule) != 0:
            return
        for fact in self.facts:
            if self._get_equality(str(data.rule.conclusion), fact):
                yield data
                return
