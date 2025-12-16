from apyds import Rule


class Poly:
    def __init__(self, **kwargs):
        ((key, value),) = kwargs.items()
        match key:
            case "ds":
                self.ds = value
                self.rule = Rule(self.ds)
            case "rule":
                self.rule = value
                self.ds = str(self.rule)
            case _:
                raise ValueError("Invalid argument for Poly")

    @property
    def idea(self):
        if not self.ds.startswith("--"):
            return Poly(ds=f"--\n{self.ds.splitlines()[0]}")
        return None
