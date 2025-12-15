from apyds import Rule
from apyds_bnf import parse, unparse


class Poly:
    def __init__(self, **kwargs):
        ((key, value),) = kwargs.items()
        match key:
            case "dsp":
                self.ds = parse(value)
                self.dsp = unparse(self.ds)
                self.rule = Rule(self.ds)
            case "ds":
                self.dsp = unparse(value)
                self.ds = parse(self.dsp)
                self.rule = Rule(self.ds)
            case "rule":
                self.rule = value
                self.ds = str(self.rule)
                self.dsp = unparse(self.ds)
            case _:
                raise ValueError("Invalid argument for Poly")

    @property
    def idea(self):
        if len(self.rule) != 0:
            return Poly(ds=f"--\n{self.rule[0]}")
        return None
