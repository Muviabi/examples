"""Run a Muvia function on your machine the way Muvia runs it, and check what it returns.

    from muvia_local import run
    outputs = run("functions/business/receivables_aging", {"invoices": invoices}, params={})

``run`` loads ``<path>.py`` and ``<path>.json`` (the pair the Lab's Import takes), hands each table
input to ``transform`` as a pandas DataFrame after a round trip through Arrow, as Muvia does, gives
it a ``ctx`` with ``logger``, ``window`` and ``preview``, and checks both sides against the contract:
the input columns it declares, then an output dict with exactly the contract's ports, each table a
DataFrame carrying the columns, and kinds, its contract promises.

This is a test bench, not Muvia: it does not limit memory or time, nor cut the network, and a
capability's handle (``ctx.notify``, ``ctx.llm``...) is not there at all.
"""

from muvia_local.bench import CapabilityMissing, ContractBroken, Window, load, run

__all__ = ["CapabilityMissing", "ContractBroken", "Window", "load", "run"]
