"""Eval-free Contract ``ExecutionTicket`` & Multi-Port Typed Computational DAG (T256-02).

Synthesized via BCEL from ``SPEACE PROTOTIPO CLAUDE`` (``neural_engine/protocol.py``,
``neural_engine/graph_core.py``, ``neural_engine/config/contracts.yaml``):
- Unsanitized ``eval()`` precondition/postcondition execution is *accidental* and eliminated.
- Declarative typed ``FieldConstraint`` / ``ContractSpec`` validation, verified
  ``ExecutionTicket`` lifecycle, explicit ``source_port -> target_port`` ``EdgeKind``
  links, Kahn cycle-rejecting topological ordering, and bounded subgraph execution
  survive as fail-closed software primitives.
"""

from __future__ import annotations

import math
import time
import uuid
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EdgeKind(StrEnum):
    """Typed inter-node edge semantics."""

    DATA = "data"
    CONTROL = "control"
    FEEDBACK = "feedback"


_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "str": (str,),
    "int": (int,),
    "float": (int, float),
    "bool": (bool,),
    "dict": (dict,),
    "list": (list, tuple),
    "any": (object,),
}


@dataclass(frozen=True)
class FieldConstraint:
    """Safe declarative constraint on one input or output field (zero ``eval()``)."""

    expected_type: str = "any"
    required: bool = True
    non_empty: bool = False
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: tuple[Any, ...] | None = None

    def __post_init__(self) -> None:
        if self.expected_type not in _TYPE_MAP:
            raise ValueError(f"Unsupported expected_type: {self.expected_type!r}")
        if self.min_value is not None and not math.isfinite(self.min_value):
            raise ValueError("min_value must be finite")
        if self.max_value is not None and not math.isfinite(self.max_value):
            raise ValueError("max_value must be finite")
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value must be <= max_value")

    def validate(self, field_name: str, payload: Mapping[str, Any]) -> list[str]:
        if field_name not in payload:
            return [f"missing required field {field_name!r}"] if self.required else []

        val = payload[field_name]
        errors: list[str] = []

        # In Python bool is a subclass of int; reject bool when int/float is requested
        if self.expected_type in ("int", "float") and isinstance(val, bool):
            errors.append(f"field {field_name!r} expected {self.expected_type}, got bool")
            return errors

        allowed_py_types = _TYPE_MAP[self.expected_type]
        if not isinstance(val, allowed_py_types):
            errors.append(
                f"field {field_name!r} expected {self.expected_type}, got {type(val).__name__}"
            )
            return errors

        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if not math.isfinite(float(val)):
                errors.append(f"field {field_name!r} must be finite")
                return errors
            if self.min_value is not None and float(val) < self.min_value:
                errors.append(f"field {field_name!r}={val} < min_value {self.min_value}")
            if self.max_value is not None and float(val) > self.max_value:
                errors.append(f"field {field_name!r}={val} > max_value {self.max_value}")

        if self.non_empty and isinstance(val, (str, list, tuple, dict)) and len(val) == 0:
            errors.append(f"field {field_name!r} must be non-empty")

        if self.allowed_values is not None and val not in self.allowed_values:
            errors.append(f"field {field_name!r}={val!r} not in {self.allowed_values!r}")

        return errors


@dataclass(frozen=True)
class ContractSpec:
    """Formal declarative I/O & resource contract for a computational node."""

    name: str
    version: str = "1.0"
    input_constraints: Mapping[str, FieldConstraint] = field(default_factory=dict)
    output_constraints: Mapping[str, FieldConstraint] = field(default_factory=dict)
    max_memory_mb: float = 256.0
    timeout_s: float = 30.0

    def __post_init__(self) -> None:
        if not self.name or not self.version:
            raise ValueError("ContractSpec name and version must be non-empty")
        if not math.isfinite(self.max_memory_mb) or self.max_memory_mb <= 0.0:
            raise ValueError("max_memory_mb must be finite and > 0")
        if not math.isfinite(self.timeout_s) or self.timeout_s <= 0.0:
            raise ValueError("timeout_s must be finite and > 0")

    def validate_inputs(self, inputs: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
        errs: list[str] = []
        for fname, rule in self.input_constraints.items():
            errs.extend(rule.validate(fname, inputs))
        return (len(errs) == 0, tuple(errs))

    def validate_outputs(self, outputs: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
        errs: list[str] = []
        for fname, rule in self.output_constraints.items():
            errs.extend(rule.validate(fname, outputs))
        return (len(errs) == 0, tuple(errs))


@dataclass
class ExecutionTicket:
    """Auditable execution ticket tracking pre-check, execution, and post-check."""

    ticket_id: str
    node_id: str
    contract: ContractSpec
    inputs: dict[str, Any]
    status: str = "pending"
    outputs: dict[str, Any] | None = None
    validation_errors: tuple[str, ...] = ()
    elapsed_s: float = 0.0


@dataclass(frozen=True)
class PortEdge:
    """Directed multi-port connection between two computational nodes."""

    edge_id: str
    source_id: str
    target_id: str
    source_port: str = "output"
    target_port: str = "input"
    kind: EdgeKind = EdgeKind.DATA
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.source_id or not self.target_id:
            raise ValueError("source_id and target_id must be non-empty")
        if not self.source_port or not self.target_port:
            raise ValueError("source_port and target_port must be non-empty")
        if not math.isfinite(self.weight) or self.weight < 0.0:
            raise ValueError("weight must be finite and >= 0")


@dataclass(frozen=True)
class DAGNodeSpec:
    """Node registered in :class:`TypedComputationalDAG`."""

    node_id: str
    fn: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    contract: ContractSpec | None = None


class TypedComputationalDAG:
    """Cycle-rejecting multi-port computational DAG with ``ExecutionTicket`` enforcement (T256-02)."""

    def __init__(self, name: str = "qspeace_dag") -> None:
        if not name:
            raise ValueError("name must be non-empty")
        self.name = name
        self._nodes: dict[str, DAGNodeSpec] = {}
        self._edges: dict[str, PortEdge] = {}
        self._topo_cache: tuple[str, ...] | None = None
        self._tickets: deque[ExecutionTicket] = deque(maxlen=256)

    @property
    def tickets(self) -> tuple[ExecutionTicket, ...]:
        return tuple(self._tickets)

    def add_node(
        self,
        node_id: str,
        fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        *,
        contract: ContractSpec | None = None,
    ) -> None:
        if not node_id:
            raise ValueError("node_id must be non-empty")
        if node_id in self._nodes:
            raise ValueError(f"Duplicate node_id: {node_id!r}")
        self._nodes[node_id] = DAGNodeSpec(node_id=node_id, fn=fn, contract=contract)
        self._topo_cache = None

    def connect(
        self,
        source_id: str,
        target_id: str,
        *,
        source_port: str = "output",
        target_port: str = "input",
        kind: EdgeKind = EdgeKind.DATA,
        weight: float = 1.0,
    ) -> PortEdge:
        if source_id not in self._nodes or target_id not in self._nodes:
            raise KeyError("Both source_id and target_id must be registered before connecting")
        if source_id == target_id and kind != EdgeKind.FEEDBACK:
            raise ValueError("Self-loops are rejected on forward DATA/CONTROL edges")

        edge_id = f"e_{uuid.uuid4().hex[:10]}"
        edge = PortEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            source_port=source_port,
            target_port=target_port,
            kind=kind,
            weight=weight,
        )
        self._edges[edge_id] = edge
        self._topo_cache = None
        try:
            # Fail-closed cycle check on forward (non-FEEDBACK) graph immediately
            self.topological_order()
        except ValueError:
            del self._edges[edge_id]
            raise
        return edge

    def topological_order(self) -> tuple[str, ...]:
        """Return deterministic Kahn topological order over forward (DATA/CONTROL) edges."""
        if self._topo_cache is not None:
            return self._topo_cache

        in_deg: dict[str, int] = dict.fromkeys(self._nodes, 0)
        adj: dict[str, list[str]] = {nid: [] for nid in self._nodes}
        for edge in self._edges.values():
            if edge.kind == EdgeKind.FEEDBACK:
                continue
            adj[edge.source_id].append(edge.target_id)
            in_deg[edge.target_id] += 1

        ready = sorted(nid for nid, deg in in_deg.items() if deg == 0)
        queue: deque[str] = deque(ready)
        order: list[str] = []

        while queue:
            nid = queue.popleft()
            order.append(nid)
            for nb in sorted(adj[nid]):
                in_deg[nb] -= 1
                if in_deg[nb] == 0:
                    queue.append(nb)

        if len(order) != len(self._nodes):
            raise ValueError("Forward DATA/CONTROL graph contains a cycle")

        self._topo_cache = tuple(order)
        return self._topo_cache

    def _subgraph_nodes(
        self,
        start_nodes: Sequence[str] | None,
        end_nodes: Sequence[str] | None,
    ) -> set[str]:
        full_order = self.topological_order()
        if not start_nodes and not end_nodes:
            return set(full_order)

        fwd: dict[str, list[str]] = {nid: [] for nid in self._nodes}
        rev: dict[str, list[str]] = {nid: [] for nid in self._nodes}
        for edge in self._edges.values():
            if edge.kind == EdgeKind.FEEDBACK:
                continue
            fwd[edge.source_id].append(edge.target_id)
            rev[edge.target_id].append(edge.source_id)

        reachable_fwd = set(full_order)
        if start_nodes:
            reachable_fwd = set()
            q: deque[str] = deque(start_nodes)
            while q:
                cur = q.popleft()
                if cur not in self._nodes:
                    raise KeyError(f"Unknown start node: {cur!r}")
                if cur in reachable_fwd:
                    continue
                reachable_fwd.add(cur)
                q.extend(fwd[cur])

        reachable_rev = set(full_order)
        if end_nodes:
            reachable_rev = set()
            q = deque(end_nodes)
            while q:
                cur = q.popleft()
                if cur not in self._nodes:
                    raise KeyError(f"Unknown end node: {cur!r}")
                if cur in reachable_rev:
                    continue
                reachable_rev.add(cur)
                q.extend(rev[cur])

        return reachable_fwd & reachable_rev

    def execute(
        self,
        initial_inputs: Mapping[str, Mapping[str, Any]] | None = None,
        *,
        start_nodes: Sequence[str] | None = None,
        end_nodes: Sequence[str] | None = None,
    ) -> dict[str, ExecutionTicket]:
        """Execute DAG (or bounded subgraph) in topological order with ``ExecutionTicket`` checks."""
        order = self.topological_order()
        active_set = self._subgraph_nodes(start_nodes, end_nodes)
        seed_map = initial_inputs or {}

        incoming_by_target: dict[str, list[PortEdge]] = {nid: [] for nid in self._nodes}
        for edge in self._edges.values():
            if edge.kind != EdgeKind.FEEDBACK:
                incoming_by_target[edge.target_id].append(edge)

        node_outputs: dict[str, dict[str, Any]] = {}
        run_tickets: dict[str, ExecutionTicket] = {}

        for nid in order:
            if nid not in active_set:
                continue
            spec = self._nodes[nid]
            merged_in: dict[str, Any] = dict(seed_map.get(nid, {}))

            blocked_upstream = False
            for edge in incoming_by_target[nid]:
                if edge.source_id not in active_set:
                    continue
                up_ticket = run_tickets.get(edge.source_id)
                if up_ticket is None or up_ticket.status != "completed":
                    blocked_upstream = True
                    break
                src_out = node_outputs.get(edge.source_id, {})
                if edge.source_port in src_out:
                    val = src_out[edge.source_port]
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        merged_in[edge.target_port] = float(val) * edge.weight
                    else:
                        merged_in[edge.target_port] = val

            contract = spec.contract or ContractSpec(name=f"implicit_{nid}")
            ticket = ExecutionTicket(
                ticket_id=f"tkt_{uuid.uuid4().hex[:10]}",
                node_id=nid,
                contract=contract,
                inputs=merged_in,
            )

            if blocked_upstream:
                ticket.status = "skipped_upstream_failure"
                self._tickets.append(ticket)
                run_tickets[nid] = ticket
                continue

            if spec.contract is not None:
                in_ok, in_errs = spec.contract.validate_inputs(merged_in)
                if not in_ok:
                    ticket.status = "input_validation_failed"
                    ticket.validation_errors = in_errs
                    self._tickets.append(ticket)
                    run_tickets[nid] = ticket
                    continue

            t0 = time.perf_counter()
            try:
                raw_out = dict(spec.fn(merged_in))
            except Exception as exc:
                ticket.elapsed_s = time.perf_counter() - t0
                ticket.status = "execution_failed"
                ticket.validation_errors = (f"{type(exc).__name__}: {exc}",)
                self._tickets.append(ticket)
                run_tickets[nid] = ticket
                continue
            ticket.elapsed_s = time.perf_counter() - t0

            if spec.contract is not None:
                out_ok, out_errs = spec.contract.validate_outputs(raw_out)
                if not out_ok:
                    ticket.status = "output_validation_failed"
                    ticket.validation_errors = out_errs
                    self._tickets.append(ticket)
                    run_tickets[nid] = ticket
                    continue

            ticket.status = "completed"
            ticket.outputs = raw_out
            node_outputs[nid] = raw_out
            self._tickets.append(ticket)
            run_tickets[nid] = ticket

        return run_tickets
