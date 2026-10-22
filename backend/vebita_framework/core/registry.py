"""
core/registry.py
================
VEBITA Algorithm Registry

Central store for all 550+ algorithms across 6 services.
Every algorithm auto-registers itself using the @registry.register decorator.

The benchmark runner asks the registry:
    "Give me all algorithms for service 5"
    "Give me all clustering algorithms"
    "Give me everything"

And runs them all automatically.
"""

from typing import Dict, List, Type, Optional
from core.base import BaseAlgorithm

class AlgorithmRegistry:
    """
    Singleton registry. All algorithms register here at import time.
    """

    def __init__(self):
        # storage: { service_id: { algo_name: AlgoClass } }
        self._store: Dict[int, Dict[str, Type[BaseAlgorithm]]] = {}
        self._all:   Dict[str, Type[BaseAlgorithm]] = {}

    # ── Registration ──────────────────────────────────────────────────────
    def register(self, cls: Type[BaseAlgorithm]) -> Type[BaseAlgorithm]:
        """
        Decorator that registers an algorithm class.

        Usage:
            @registry.register
            class MyAlgo(BaseAlgorithm):
                ...
        """
        sid  = cls.service_id
        name = cls.name

        if sid not in self._store:
            self._store[sid] = {}

        if name in self._store.get(sid, {}):
            raise ValueError(
                f"Algorithm '{name}' already registered for service {sid}. "
                f"Each algorithm needs a unique name within its service."
            )

        self._store[sid][name] = cls
        self._all[f"S{sid}::{name}"] = cls
        return cls

    # ── Querying ──────────────────────────────────────────────────────────
    def get_all(self) -> List[Type[BaseAlgorithm]]:
        """Return all registered algorithms across all services."""
        return list(self._all.values())

    def get_by_service(self, service_id: int) -> List[Type[BaseAlgorithm]]:
        """Return all algorithms for a specific service (1–6)."""
        return list(self._store.get(service_id, {}).values())

    def get_by_category(self, category: str) -> List[Type[BaseAlgorithm]]:
        """Return all algorithms of a given category across all services."""
        return [
            cls for cls in self._all.values()
            if cls.category.lower() == category.lower()
        ]

    def get_by_name(self, name: str,
                    service_id: Optional[int] = None) -> Optional[Type[BaseAlgorithm]]:
        """Look up a specific algorithm by name."""
        if service_id is not None:
            return self._store.get(service_id, {}).get(name)
        for cls in self._all.values():
            if cls.name == name:
                return cls
        return None

    # ── Reporting ─────────────────────────────────────────────────────────
    def summary(self) -> dict:
        """Print a summary of all registered algorithms."""
        total = len(self._all)
        by_service = {
            sid: len(algos)
            for sid, algos in self._store.items()
        }
        categories = {}
        for cls in self._all.values():
            cat = cls.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total":      total,
            "by_service": by_service,
            "by_category": categories,
        }

    def print_summary(self):
        s = self.summary()
        print(f"\n{'='*50}")
        print(f"  VEBITA Algorithm Registry")
        print(f"  Total algorithms registered: {s['total']}")
        print(f"{'='*50}")
        service_names = {
            1: "Time Series",
            2: "Pattern Recognition",
            3: "Environmental Factors",
            4: "Anomaly Detection",
            5: "Trajectory Segmentation",
            6: "Behavioural Classification",
        }
        for sid in sorted(s["by_service"]):
            print(f"  S{sid} {service_names.get(sid,''):<30} {s['by_service'][sid]:>3} algorithms")
        print(f"{'-'*50}")
        print(f"  By category:")
        for cat, count in sorted(s["by_category"].items(), key=lambda x: -x[1]):
            print(f"    {cat:<25} {count:>3}")
        print(f"{'='*50}\n")


# ── Global singleton ──────────────────────────────────────────────────────
registry = AlgorithmRegistry()
