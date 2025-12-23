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
        # Cache for optimization: maps fact to its equivalent terms
        self.fact_equiv_cache: dict[Term, set[Term]] = {}

    def rebuild(self) -> None:
        self.egraph.rebuild()
        # Build pairs as before
        for lhs in self.terms:
            for rhs in self.terms:
                if self.egraph.get_equality(lhs, rhs):
                    equality = _build_lhs_rhs_to_term(lhs, rhs)
                    self.pairs.add(equality)

        # Build fact equivalence cache for optimization
        self.fact_equiv_cache.clear()
        for fact in self.facts:
            equiv_terms = set()
            for term in self.terms:
                if self.egraph.get_equality(fact, term):
                    equiv_terms.add(term)
            self.fact_equiv_cache[fact] = equiv_terms

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

    def _collect_matching_candidates(self, pattern: Term, candidates: set[Term]) -> list[Term]:
        """Collect all candidates that can potentially match the pattern.

        Uses the @ operator (unification) to check if pattern can match each candidate.
        The @ operator attempts to unify two terms, returning a substitution if successful.

        Args:
            pattern: The pattern term to match against
            candidates: Set of candidate terms to check

        Returns:
            List of candidates that can unify with the pattern
        """
        result = []
        for candidate in candidates:
            if pattern @ candidate:  # Unification check
                result.append(candidate)
        return result

    def _group_by_equivalence_class(self, terms: list[Term]) -> list[list[Term]]:
        """Group terms by their equivalence classes in the egraph."""
        if not terms:
            return []

        # Map each term to its representative (canonical form)
        term_to_repr: dict[Term, EClassId] = {}
        for term in terms:
            term_to_repr[term] = self.egraph.core.find(self.egraph._get_or_add(term))

        # Group terms by representative
        repr_to_terms: dict[EClassId, list[Term]] = {}
        for term, repr_id in term_to_repr.items():
            if repr_id not in repr_to_terms:
                repr_to_terms[repr_id] = []
            repr_to_terms[repr_id].append(term)

        return list(repr_to_terms.values())

    def execute(self, data: Rule) -> typing.Iterator[Rule]:
        yield from self._execute_expr(data)
        yield from self._execute_fact(data)

    def _execute_expr(self, data: Rule) -> typing.Iterator[Rule]:
        """Execute equality query: Q := A == B

        Optimized approach:
        1. Collect A_pool = all terms x where A can match x
        2. Collect B_pool = all terms y where B can match y
        3. Group both pools by equivalence classes
        4. For each pair of equivalent groups, check matches
        """
        lhs_rhs = _extract_lhs_rhs_from_rule(data)
        if lhs_rhs is None:
            return
        lhs, rhs = lhs_rhs

        # 检查是否已经存在严格相等的事实
        if self.egraph.get_equality(lhs, rhs):
            yield data

        # 尝试处理含有变量的情况
        # Optimization: Collect candidates that can match lhs and rhs
        lhs_pool = self._collect_matching_candidates(lhs, self.terms)
        rhs_pool = self._collect_matching_candidates(rhs, self.terms)

        if not lhs_pool or not rhs_pool:
            return

        # Group by equivalence classes
        lhs_groups = self._group_by_equivalence_class(lhs_pool)
        rhs_groups = self._group_by_equivalence_class(rhs_pool)

        # Match groups that are equivalent
        for lhs_group in lhs_groups:
            for rhs_group in rhs_groups:
                # Check if these groups are equivalent
                if lhs_group and rhs_group:
                    # Use the first element as representative of the equivalence class
                    if self.egraph.get_equality(lhs_group[0], rhs_group[0]):
                        # Try to match within this equivalence class
                        for x in lhs_group:
                            for y in rhs_group:
                                # Build the equality term and check if it matches the query
                                target = _build_lhs_rhs_to_term(x, y)
                                query = data.conclusion
                                if unification := target @ query:
                                    if result := target.ground(unification, scope="1"):
                                        yield _build_term_to_rule(result)

    def _execute_fact(self, data: Rule) -> typing.Iterator[Rule]:
        """Execute fact query: Q := A

        Optimized approach:
        1. Collect A_pool = all terms x where A can match x
        2. For each fact F, use cached equivalent terms (F_pool)
        3. Group both pools by equivalence classes
        4. For each pair of equivalent groups, check matches
        """
        if len(data) != 0:
            return
        idea = data.conclusion

        # 检查是否已经存在严格相等的事实
        for fact in self.facts:
            if self.egraph.get_equality(idea, fact):
                yield data

        # 尝试处理含有变量的情况
        # Optimization: Collect candidates that can match the idea
        idea_pool = self._collect_matching_candidates(idea, self.terms)

        if not idea_pool:
            return

        # Group idea_pool by equivalence classes
        idea_groups = self._group_by_equivalence_class(idea_pool)

        # For each fact, check if it matches with idea through equivalence
        for fact in self.facts:
            # Get cached equivalent terms for this fact
            fact_pool = self.fact_equiv_cache.get(fact, set())
            if not fact_pool:
                continue

            # Group fact_pool by equivalence classes
            fact_groups = self._group_by_equivalence_class(list(fact_pool))

            # Match groups that are equivalent
            for idea_group in idea_groups:
                for fact_group in fact_groups:
                    # Check if these groups are equivalent
                    if idea_group and fact_group:
                        # Use the first element as representative of the equivalence class
                        if self.egraph.get_equality(idea_group[0], fact_group[0]):
                            # Try to match within this equivalence class
                            for x in idea_group:
                                for y in fact_group:
                                    # Build the equality query and check matches
                                    # target is (x == y), query is (idea == fact)
                                    target = _build_lhs_rhs_to_term(x, y)
                                    query = _build_lhs_rhs_to_term(idea, fact)
                                    if unification := target @ query:
                                        if result := target.ground(unification, scope="1"):
                                            term = result.term
                                            if isinstance(term, List):
                                                yield _build_term_to_rule(term[2])
