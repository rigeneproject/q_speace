from typing import Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from speace_core.dna.models import ConnectomeGeneSet


class InterRegionConnection(BaseModel):
    source_region_id: str
    target_region_id: str
    connection_type: str = "feedforward"
    strength: float = 0.5
    plasticity_enabled: bool = True
    inhibitory: bool = False


class RegionConnectome(BaseModel):
    regions: Dict[str, dict] = Field(default_factory=dict)
    connections: List[InterRegionConnection] = Field(default_factory=list)

    def add_connection(
        self,
        source_region_id: str,
        target_region_id: str,
        connection_type: str = "feedforward",
        strength: float = 0.5,
        plasticity_enabled: bool = True,
        inhibitory: bool = False,
    ) -> InterRegionConnection:
        conn = InterRegionConnection(
            source_region_id=source_region_id,
            target_region_id=target_region_id,
            connection_type=connection_type,
            strength=strength,
            plasticity_enabled=plasticity_enabled,
            inhibitory=inhibitory,
        )
        self.connections.append(conn)
        return conn

    def get_connections_from(
        self, source_region_id: str
    ) -> List[InterRegionConnection]:
        return [c for c in self.connections if c.source_region_id == source_region_id]

    def get_connections_to(
        self, target_region_id: str
    ) -> List[InterRegionConnection]:
        return [c for c in self.connections if c.target_region_id == target_region_id]

    def remove_connections_involving(self, region_id: str) -> None:
        self.connections = [
            c
            for c in self.connections
            if c.source_region_id != region_id and c.target_region_id != region_id
        ]

    def compute_connectome_density(self) -> float:
        n = len(self.regions)
        if n < 2:
            return 0.0
        max_possible = n * (n - 1)
        return len(self.connections) / max_possible

    def apply_genome_genes(self, genes: "ConnectomeGeneSet") -> int:
        """Modifica la struttura del connettoma in base ai geni del genoma.

        I geni controllano:
        - connectivity_density → numero di connessioni aggiunte
        - hub_formation → forza delle connessioni verso regioni hub
        - modularity → probabilita' di connessioni intra-cluster
        - long_range_connections → probabilita' di connessioni tra regioni distanti
        - small_world_bias → bilanciamento locale/globale
        - redundancy → connessioni ridondanti

        Returns: numero di connessioni aggiunte/modificate.
        """
        import random

        if len(self.regions) < 2:
            return 0

        region_ids = list(self.regions.keys())
        added = 0

        target_density = 0.2 + genes.connectivity_density * 0.6
        current_density = self.compute_connectome_density()

        # Aggiungi connessioni fino a raggiungere la densita' target
        max_iterations = len(region_ids) * 3
        for _ in range(max_iterations):
            if current_density >= target_density:
                break
            src = random.choice(region_ids)
            tgt = random.choice(region_ids)
            if src == tgt:
                continue

            existing_pairs = {(c.source_region_id, c.target_region_id) for c in self.connections}
            if (src, tgt) in existing_pairs:
                continue

            # Hub formation: i nodi con piu' connessioni attirano piu' connessioni
            hub_bonus = 0.0
            if genes.hub_formation > 0.5:
                out_deg = len(self.get_connections_from(src))
                in_deg = len(self.get_connections_to(tgt))
                hub_bonus = (out_deg + in_deg) / max(len(self.regions), 1) * genes.hub_formation

            # Modularity bias: favorisci connessioni intra-cluster
            modularity_bonus = 0.0
            if genes.modularity > 0.3:
                src_community = None
                tgt_community = None
                for c in self.connections:
                    if c.source_region_id == src:
                        src_community = c.connection_type
                    if c.target_region_id == tgt:
                        tgt_community = c.connection_type
                if src_community and src_community == tgt_community:
                    modularity_bonus = genes.modularity * 0.3

            # Long-range bias: connessioni tra regioni funzionalmente distanti
            long_range_bonus = 0.0
            if genes.long_range_connections > 0.3 and src != tgt:
                conn_types_src = {c.connection_type for c in self.get_connections_from(src)}
                conn_types_tgt = {c.connection_type for c in self.get_connections_to(tgt)}
                overlap = conn_types_src & conn_types_tgt
                if len(overlap) < 2:
                    long_range_bonus = genes.long_range_connections * 0.2

            # Small-world bias: bilancia connessioni locali e globali
            small_world_mod = 1.0 + (genes.small_world_bias - 0.5) * 0.4

            # Probabilita' totale di aggiungere questa connessione
            prob = (0.3 + hub_bonus + modularity_bonus + long_range_bonus) * small_world_mod
            if random.random() < min(1.0, prob):
                strength = 0.3 + genes.connectivity_density * 0.4
                strength += hub_bonus * 0.3
                self.add_connection(
                    source_region_id=src,
                    target_region_id=tgt,
                    connection_type="genetic",
                    strength=min(1.0, strength),
                    plasticity_enabled=genes.plasticity > 0.3,
                    inhibitory=False,
                )
                added += 1
                current_density = self.compute_connectome_density()

        # Ridondanza: aggiungi connessioni parallele se il gene e' alto
        if genes.redundancy > 0.6 and self.connections:
            redundant_count = int(len(self.connections) * genes.redundancy * 0.1)
            existing_pairs = {(c.source_region_id, c.target_region_id) for c in self.connections}
            for _ in range(redundant_count):
                if existing_pairs:
                    pair = random.choice(list(existing_pairs))
                    self.add_connection(
                        source_region_id=pair[0],
                        target_region_id=pair[1],
                        connection_type="redundant",
                        strength=0.2,
                        plasticity_enabled=True,
                        inhibitory=False,
                    )
                    added += 1

        return added
