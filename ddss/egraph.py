from __future__ import annotations
import typing
from collections import defaultdict
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

    def find(self, data: Term) -> EClassId:
        data_id = self._get_or_add(data)
        return self.core.find(data_id)

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
        self.newly_added_terms: set[Term] = set()
        self.newly_added_facts: set[Term] = set()
        self.fact_equiv_cache: dict[Term, set[Term]] = defaultdict(set)

    def rebuild(self) -> None:
        self.egraph.rebuild()
        for fact in self.facts:
            for term in self.newly_added_terms:
                if self.egraph.get_equality(fact, term):
                    self.fact_equiv_cache[fact].add(term)
        for fact in self.newly_added_facts:
            for term in self.terms:
                if self.egraph.get_equality(fact, term):
                    self.fact_equiv_cache[fact].add(term)
        for fact in self.newly_added_facts:
            for term in self.newly_added_terms:
                if self.egraph.get_equality(fact, term):
                    self.fact_equiv_cache[fact].add(term)
        self.newly_added_terms.clear()
        self.newly_added_facts.clear()

    def add(self, data: Rule) -> None:
        self._add_expr(data)
        self._add_fact(data)

    def _add_expr(self, data: Rule) -> None:
        lhs_rhs = _extract_lhs_rhs_from_rule(data)
        if lhs_rhs is None:
            return
        lhs, rhs = lhs_rhs
        self.terms.add(lhs)
        self.newly_added_terms.add(lhs)
        self.terms.add(rhs)
        self.newly_added_terms.add(rhs)
        self.egraph.set_equality(lhs, rhs)

    def _add_fact(self, data: Rule) -> None:
        if len(data) != 0:
            return
        term = data.conclusion
        self.terms.add(term)
        self.newly_added_terms.add(term)
        self.facts.add(term)
        self.newly_added_facts.add(term)

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
        lhs_pool = self._collect_matching_candidates(lhs, self.terms)
        rhs_pool = self._collect_matching_candidates(rhs, self.terms)

        if not lhs_pool or not rhs_pool:
            return

        lhs_groups = self._group_by_equivalence_class(lhs_pool)
        rhs_groups = self._group_by_equivalence_class(rhs_pool)

        for lhs_group in lhs_groups:
            for rhs_group in rhs_groups:
                if lhs_group and rhs_group:
                    if self.egraph.get_equality(next(iter(lhs_group)), next(iter(rhs_group))):
                        for x in lhs_group:
                            for y in rhs_group:
                                target = _build_lhs_rhs_to_term(x, y)
                                query = data.conclusion
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
        idea_pool = self._collect_matching_candidates(idea, self.terms)

        if not idea_pool:
            return

        idea_groups = self._group_by_equivalence_class(idea_pool)

        for fact in self.facts:
            fact_pool = self.fact_equiv_cache[fact]
            if not fact_pool:
                continue

            fact_groups = self._group_by_equivalence_class(fact_pool)

            for idea_group in idea_groups:
                for fact_group in fact_groups:
                    if idea_group and fact_group:
                        if self.egraph.get_equality(next(iter(idea_group)), next(iter(fact_group))):
                            for x in idea_group:
                                for y in fact_group:
                                    target = _build_lhs_rhs_to_term(x, y)
                                    query = _build_lhs_rhs_to_term(idea, fact)
                                    if unification := target @ query:
                                        if result := target.ground(unification, scope="1"):
                                            term = result.term
                                            if isinstance(term, List):
                                                yield _build_term_to_rule(term[2])

    def _collect_matching_candidates(self, pattern: Term, candidates: set[Term]) -> set[Term]:
        result = set()
        for candidate in candidates:
            if pattern @ candidate:
                result.add(candidate)
        return result

    def _group_by_equivalence_class(self, terms: set[Term]) -> typing.Iterable[set[Term]]:
        if not terms:
            return []

        term_to_eid: dict[Term, EClassId] = {}
        for term in terms:
            term_to_eid[term] = self.egraph.find(term)

        eid_to_terms: dict[EClassId, set[Term]] = defaultdict(set)
        for term, eid in term_to_eid.items():
            eid_to_terms[eid].add(term)
        return eid_to_terms.values()
