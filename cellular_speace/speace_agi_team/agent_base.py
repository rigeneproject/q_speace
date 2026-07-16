"""Base agent class — all agents use local Ollama with gemma4:12b by default.

Fallback chain (only used when local Ollama is unreachable):
  1. glm-5.1:cloud / deepseek-v4-pro:cloud (premium, API key required)
  2. gemma3:12b / llama3.1:8b / qwen3.5:4b / gemma3:4b (free Ollama Cloud)
"""

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from speace_agi_team.action_catalog import ActionCatalog, ActionCategory, ActionRiskLevel
from speace_agi_team.action_proposal import ActionProposal, ActionProposalStatus, ActionRiskLevel as ProposalRiskLevel
from speace_agi_team.config import AgentConfig
from speace_agi_team.web_search import DocumentFetcher, WebSearcher, research

_logger = logging.getLogger(__name__)


class AgentBase:
    def __init__(self, agent_id: str, name: str, role: str, description: str,
                 system_instruction: str = "", config: Optional[AgentConfig] = None,
                 agent_type: str = "technician"):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.agent_type: str = agent_type
        self.description = description
        self.config = config or AgentConfig()
        web_tool_hint = (
            "\n\n[Strumenti web] Puoi effettuare ricerche sul web e leggere "
            "documenti tecnici/scientifici tramite i metodi self.search_web(query) e "
            "self.fetch_url(url). Usali per raccogliere informazioni aggiornate e "
            "produrre raccomandazioni basate su letteratura recente."
        )
        self.system_prompt = (
            f"{self.config.system_prompt_prefix}\n\nRuolo: {role}\n\n"
            f"Istruzioni specifiche: {system_instruction}{web_tool_hint}"
        )
        self.conversation_history: List[Dict[str, str]] = []
        self.tasks: List[Dict] = []
        self.findings: List[Dict] = []
        self._findings_lock = threading.Lock()
        self.research_history: List[Dict] = []  # log delle ricerche web
        self.status = "idle"
        self.current_model_level: str = "primary"
        self.active_model: str = config.model if config else ""
        # Lazily-initialized web tools
        self._searcher: Optional[WebSearcher] = None
        self._fetcher: Optional[DocumentFetcher] = None

    # ── Web tools (lazy initialization) ───────────────────────────
    @property
    def searcher(self) -> WebSearcher:
        if self._searcher is None:
            self._searcher = WebSearcher()
        return self._searcher

    @property
    def fetcher(self) -> DocumentFetcher:
        if self._fetcher is None:
            self._fetcher = DocumentFetcher()
        return self._fetcher

    def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Run a DuckDuckGo search and remember the results."""
        results = self.searcher.search(query, max_results=max_results)
        self.research_history.append({
            "ts": time.time(),
            "type": "search",
            "query": query,
            "results_count": len(results) if results else 0,
        })
        return results

    def fetch_url(self, url: str) -> Dict[str, Any]:
        """Fetch a URL and return extracted text. Tracked in research history."""
        doc = self.fetcher.fetch(url)
        self.research_history.append({
            "ts": time.time(),
            "type": "fetch",
            "url": url,
            "status": doc.get("status", 0),
            "length": doc.get("length", 0),
            "error": doc.get("error"),
        })
        return doc

    def research_web(self, query: str, max_results: int = 5, fetch_top: int = 2,
                     fetch_max_chars: int = 8000) -> Dict[str, Any]:
        """High-level research: search + fetch top results, in a single call."""
        result = research(query, max_results=max_results, fetch_top=fetch_top,
                          fetch_max_chars=fetch_max_chars)
        self.research_history.append({
            "ts": time.time(),
            "type": "research",
            "query": query,
            "results_count": len(result.get("results", [])),
            "documents_count": len(result.get("documents", [])),
        })
        return result

    def research_summary(self, query: str, fetch_top: int = 2,
                          fetch_max_chars: int = 6000) -> str:
        """Research + return a formatted text block for prompt injection."""
        data = self.research_web(query, max_results=5, fetch_top=fetch_top,
                                 fetch_max_chars=fetch_max_chars)
        lines = [f"## Risultati web per: {query}\n"]
        for i, r in enumerate(data.get("results", []), 1):
            lines.append(f"### [{i}] {r.get('title','')}")
            lines.append(f"URL: {r.get('url','')}")
            if r.get("snippet"):
                lines.append(f"Snippet: {r['snippet']}")
            lines.append("")
        for i, d in enumerate(data.get("documents", []), 1):
            lines.append(f"### Documento [{i}]: {d.get('title','')}")
            lines.append(f"URL: {d.get('url','')} ({d.get('length',0)} caratteri)")
            if d.get("text"):
                lines.append("Contenuto estratto:")
                lines.append(d["text"][:fetch_max_chars])
            elif d.get("error"):
                lines.append(f"Errore: {d['error']}")
            lines.append("")
        if not data.get("results"):
            lines.append("(Nessun risultato trovato)")
        return "\n".join(lines)


    def _chat_with_retry(self, prompt: str, max_retries: int = 2) -> str:
        """Call self.chat() with a retry-on-truncation policy.

        If the response looks truncated (ends mid-sentence, no terminal
        punctuation, or signals 'truncated' / 'output parziale' in italian
        prompts), the call is retried up to max_retries times with a short
        continuation prompt.
        """
        last = self.chat(prompt)
        for _ in range(max_retries):
            if not self._looks_truncated(last):
                return last
            cont = self.chat(prompt + "\n\n[Continua esattamente da dove ti sei interrotto.]")
            last = last + " " + cont
        return last

    @staticmethod
    def _looks_truncated(text: str) -> bool:
        if not text:
            return True
        t = text.rstrip()
        if not t:
            return True
        if t[-1] not in ".!?)}\"':":
            return True
        if "truncat" in t.lower() or "parziale" in t.lower():
            return True
        return False

    def get_research_history(self, n: int = 20) -> List[Dict[str, Any]]:
        return self.research_history[-n:]

    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in self.conversation_history[-20:]:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(self, message: str) -> str:
        """Send a message to the LLM with per-call fallback chain.

        Timeout: 30s primary, 45s fallback.
        On failure: tries the next model in MODEL_CHAIN.
        Error messages are NOT stored in conversation history (to prevent
        pollution from cascading timeouts).
        """
        self.status = "thinking"
        from speace_agi_team.config import MODEL_CHAIN, _is_ollama_local_running, OLLAMA_LOCAL_HOST, OLLAMA_LOCAL_PORT

        # Build the fallback chain: LOCAL OLLAMA PRIMARY, then cloud fallbacks
        fallback_chain = []

        # 1. Local Ollama — PRIMARY (tried first)
        if _is_ollama_local_running(OLLAMA_LOCAL_HOST, OLLAMA_LOCAL_PORT):
            fallback_chain.append({
                "model": "gemma4:12b",
                "endpoint": f"http://{OLLAMA_LOCAL_HOST}:{OLLAMA_LOCAL_PORT}",
                "api_key": "",
                "is_openai_compatible": False,
                "provider": "ollama_local",
            })

        # 2. Cloud models — premium first (if API key), then free
        for entry in MODEL_CHAIN:
            # Skip local entries (already added above if running)
            if entry.get("provider", "").startswith("ollama_local"):
                continue
            api_key = entry.get("api_key", "")
            if entry.get("needs_auth", False) and not api_key:
                continue  # skip auth-required models that have no key
            fallback_chain.append({
                "model": entry["model"],
                "endpoint": entry["endpoint"],
                "api_key": api_key,
                "is_openai_compatible": True,
                "provider": entry["provider"],
            })

        # If fallback chain is empty, use the default config
        if not fallback_chain:
            fallback_chain = [{
                "model": self.config.model,
                "endpoint": self.config.endpoint,
                "api_key": self.config.api_key,
                "is_openai_compatible": self.config.is_openai_compatible,
                "provider": self.config.provider,
            }]

        last_error = None
        previous_model = fallback_chain[0]["model"] if fallback_chain else "unknown"
        for attempt, model_config in enumerate(fallback_chain):
            try:
                messages = self._build_messages(message)
                model = model_config.get("model", self.config.model)
                endpoint = model_config.get("endpoint", self.config.endpoint)
                api_key = model_config.get("api_key", self.config.api_key)
                is_openai = model_config.get("is_openai_compatible", self.config.is_openai_compatible)

                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "stream": False,
                }

                # Longer timeout for primary (45s), shorter for fallbacks (25s)
                # Free cloud models can be slow with long prompts
                timeout = 45.0 if attempt == 0 else 25.0

                if is_openai:
                    api_path = f"{endpoint}/chat/completions"
                else:
                    api_path = f"{endpoint}/api/chat"

                with httpx.Client(timeout=timeout) as client:
                    headers = {"Content-Type": "application/json"}
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                    resp = client.post(
                        api_path,
                        json=payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    if is_openai:
                        content = (
                            result.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                    else:
                        content = result.get("message", {}).get("content", "")

                    # Track active model and fallback level
                    self.active_model = model
                    self.current_model_level = "fallback" if attempt > 0 else "primary"

                    # Only store successful responses in conversation history
                    self.conversation_history.append({"role": "user", "content": message})
                    self.conversation_history.append({"role": "assistant", "content": content})
                    self.status = "idle"
                    return content

            except Exception as e:
                last_error = e
                next_model = fallback_chain[attempt + 1]["model"] if attempt + 1 < len(fallback_chain) else "none"
                _logger.warning(
                    "llm_fallback from_model=%s to_model=%s reason=%s",
                    model_config.get("model", "unknown"),
                    next_model,
                    str(e),
                )
                previous_model = model_config.get("model", "unknown")
                continue

        # All fallbacks failed — try rule-based fallback analysis
        self.status = "error"
        _logger.error("All LLM fallbacks failed for agent %s: %s", self.agent_id, last_error)

        # Generate rule-based fallback response for analysis prompts
        if "Analizza" in message or "analizza" in message or "contest" in message.lower() or "SPEACE" in message:
            fallback = self._rule_based_analysis(message)
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": fallback})
            self.status = "idle"
            return fallback

        error_msg = f"ERRORE: tutti i modelli LLM hanno fallito — ultimo errore: {last_error}"
        # Do NOT store error messages in conversation history to prevent pollution
        return error_msg

    def _rule_based_analysis(self, message: str) -> str:
        """Generate a rule-based analysis when all LLM models fail.

        Uses the agent's domain knowledge and context to produce
        a basic but actionable analysis without an LLM.
        """
        # Extract key metrics from recent conversation or context
        lines = [
            f"[ANALISI AUTOMATICA — {self.name} ({self.agent_id})]",
            "Il servizio LLM non è disponibile. Analisi basata su regole.",
            "",
        ]

        # Domain-specific rule-based analysis
        domain = self.role.lower() if self.role else ""
        agent_id = self.agent_id.lower()

        if "brain" in domain or "neur" in agent_id or "sinaps" in agent_id or "region" in agent_id:
            lines.extend([
                "OSSERVAZIONI (dominio cerebrale):",
                "- Coerenza φ bassa indica neuroni insufficientemente attivi",
                "- L'energia neuronale può essere insufficiente",
                "- Le sinapsi potrebbero aver bisogno di rinforzo",
                "",
                "RACCOMANDAZIONI:",
                "1. inject_neuron_energy: iniettare energia nei neuroni a bassa energia",
                "2. activate_stalled_neurons: attivare neuroni stallati",
                "3. adjust_plasticity_rate: aumentare il tasso di plasticità",
            ])
        elif "organ" in domain or "runtime" in agent_id or "defense" in agent_id:
            lines.extend([
                "OSSERVAZIONI (dominio organismo/runtime):",
                "- Il sistema potrebbe essere in stallo (tick non avanzanti)",
                "- La salute del sistema potrebbe essere degradata",
                "",
                "RACCOMANDAZIONI:",
                "1. force_advance_tick: forzare l'avanzamento del tick",
                "2. trigger_recovery: innescare il recovery del sistema",
                "3. adjust_circadian_params: aggiustare i parametri circadiani",
            ])
        elif "memor" in domain or "memory" in agent_id:
            lines.extend([
                "OSSERVAZIONI (dominio memoria):",
                "- La consolidazione della memoria potrebbe essere compromessa",
                "- La soglia di consolidazione potrebbe necessitare aggiustamento",
                "",
                "RACCOMANDAZIONI:",
                "1. adjust_consolidation_threshold: abbassare la soglia di consolidamento",
                "2. toggle_semantic_memory: assicurarsi che la memoria semantica sia attiva",
                "3. write_memory_diagnostic: scrivere un diagnostico della memoria",
            ])
        elif "dna" in domain or "genome" in agent_id or "evolution" in agent_id:
            lines.extend([
                "OSSERVAZIONI (dominio DNA/evoluzione):",
                "- I parametri genetici potrebbero necessitare di aggiustamento",
                "- L'evoluzione potrebbe essere stagnante",
                "",
                "RACCOMANDAZIONI:",
                "1. modify_genome_yaml: aggiustare i parametri del genoma",
                "2. trigger_evolution_cycle: innescare un ciclo evolutivo",
                "3. modify_evolution_params: modificare i parametri evolutivi",
            ])
        elif "embod" in domain or "embodiment" in agent_id:
            lines.extend([
                "OSSERVAZIONI (dominio embodimento):",
                "- I sensori potrebbero essere malfunzionanti",
                "- L'adattamento embodiale potrebbe necessitare di reset",
                "",
                "RACCOMANDAZIONI:",
                "1. trigger_parameter_reset: resettare i parametri embodiali",
                "2. modify_embodiment_config: aggiornare la configurazione embodiale",
                "3. write_embodiment_diagnostic: scrivere un diagnostico",
            ])
        elif "chief" in agent_id or "architect" in agent_id:
            lines.extend([
                "OSSERVAZIONI (supervisione generale):",
                "- Il sistema presenta anomalia — LLM non disponibile",
                "- Le metriche chiave potrebbero indicare stallo o degrado",
                "",
                "RACCOMANDAZIONI PRIORITARIE:",
                "1. activate_stalled_neurons: attivare neuroni stallati per ripristinare coerenza",
                "2. inject_neuron_energy: iniettare energia nei neuroni a bassa energia",
                "3. force_advance_tick: se il tick è fermo, forzare l'avanzamento",
                "4. reset_neuron_activations: se la coerenza non si ripristina, reset attivazioni",
                "",
                "NOTA: Queste raccomandazioni sono generate automaticamente senza LLM.",
                "Quando il servizio LLM sarà disponibile, l'analisi sarà più approfondita.",
            ])
        else:
            lines.extend([
                "OSSERVAZIONI (generiche):",
                "- Il servizio LLM non è disponibile per l'analisi",
                "- Il sistema potrebbe presentare anomalie nella coerenza o nell'energia",
                "",
                "RACCOMANDAZIONI:",
                "1. trigger_recovery: innescare il recovery del sistema",
                "2. write_runtime_diagnostic: scrivere un diagnostico runtime",
                "3. Controllare le metriche di coerenza e salute",
            ])

        return "\n".join(lines)

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        context_str = json.dumps(context, indent=2, default=str)[:4000]
        prompt = (
            f"Analizza il seguente contesto di SPEACE e fornisci:\n"
            f"1. Osservazioni e anomalie rilevate\n"
            f"2. Raccomandazioni specifiche\n"
            f"3. Priorità di intervento (alta/media/bassa)\n\n"
            f"Contesto:\n{context_str}"
        )
        response = self.chat(prompt)
        finding = {
            "timestamp": time.time(),
            "agent_id": self.agent_id,
            "analysis": response,
            "context_summary": {k: v for k, v in context.items() if isinstance(v, (str, int, float, bool))},
        }
        self.findings.append(finding)
        return finding

    def assign_task(self, task: Dict) -> None:
        task["agent_id"] = self.agent_id
        task["status"] = "assigned"
        task["created_at"] = time.time()
        self.tasks.append(task)

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "type": self.agent_type,
            "description": self.description,
            "status": self.status,
            "tasks_count": len(self.tasks),
            "findings_count": len(self.findings),
            "conversation_length": len(self.conversation_history),
            "research_count": len(self.research_history),
            "model": self.config.model,
            "active_model": self.active_model,
            "model_level": self.current_model_level,
        }

    def get_conversation(self) -> List[Dict[str, str]]:
        return self.conversation_history

    def clear_conversation(self) -> None:
        self.conversation_history = []

    # ── Action proposal & execution ──────────────────────────────────

    @property
    def action_catalog(self) -> ActionCatalog:
        """Lazy-initialized action catalog for this agent."""
        if not hasattr(self, '_action_catalog') or self._action_catalog is None:
            self._action_catalog = ActionCatalog()
        return self._action_catalog

    def propose_action(
        self,
        action_type: str,
        target: str,
        new_value: Any = None,
        operation: str = "set",
        justification: str = "",
        evidence: Optional[Dict[str, Any]] = None,
        old_value: Any = None,
    ) -> Optional[ActionProposal]:
        """Propose an action based on agent analysis.

        Validates that the agent is authorized for this action category and target
        before creating the proposal.

        Returns an ActionProposal if authorized, None otherwise.
        """
        # Infer category from action_type and target
        category = self.action_catalog.infer_category(action_type, target)

        # Check authorization
        if not self.action_catalog.is_authorized(self.agent_id, category, target):
            _logger.warning(
                "Agent %s not authorized for %s:%s — proposal blocked",
                self.agent_id, category, target,
            )
            return None

        # Determine risk level
        risk_level = self.action_catalog.get_risk_level(self.agent_id, category, target)

        # Capture old_value from orchestrator if available and not provided
        if old_value is None and hasattr(self, '_orchestrator') and self._orchestrator is not None:
            old_value = getattr(self._orchestrator, target, None)

        proposal = ActionProposal(
            agent_id=self.agent_id,
            action_type=action_type,
            action_category=category,
            target=target,
            operation=operation,
            old_value=old_value,
            new_value=new_value,
            risk_level=risk_level,
            justification=justification,
            evidence=evidence or {},
        )
        return proposal

    def propose_action_from_analysis(
        self,
        context: Dict[str, Any],
        executor: Any = None,
    ) -> List[ActionProposal]:
        """Prompt the LLM with available actions and parse proposals from the response.

        The LLM receives the agent's action catalog and current context, then
        proposes actions in a structured JSON format.

        For supervisors, includes domain-specific metrics and prioritization guidance.

        Returns a list of ActionProposals (only authorized ones are included).
        """
        catalog_summary = self.action_catalog.get_summary(self.agent_id)
        context_str = json.dumps(context, indent=2, default=str)[:3000]

        # Domain-specific metrics for supervisors
        metrics_section = ""
        key_metrics = []
        if "coherence_phi" in context:
            key_metrics.append(f"- Coerenza φ: {context['coherence_phi']:.4f}")
        if "mean_energy" in context:
            key_metrics.append(f"- Energia media: {context['mean_energy']:.4f}")
        if "health_score" in context:
            key_metrics.append(f"- Salute: {context['health_score']:.4f}")
        if "cpu" in context:
            key_metrics.append(f"- CPU: {context['cpu']}")
        if "memory" in context:
            key_metrics.append(f"- Memoria: {context['memory']}")
        if "tick" in context:
            key_metrics.append(f"- Tick: {context['tick']}")
        if "plan_progress" in context:
            key_metrics.append(f"- Progresso piano: {context['plan_progress']:.1%}" if isinstance(context['plan_progress'], float) else f"- Progresso piano: {context['plan_progress']}")
        if key_metrics:
            metrics_section = "\nMetriche chiave:\n" + "\n".join(key_metrics) + "\n"

        is_supervisor = self.agent_type == "supervisor" or self.agent_id.endswith("_supervisor") or self.agent_id == "chief_architect"

        # Add stall detection context
        stall_section = ""
        if context.get("stall_detected"):
            stall_count = context.get("stall_count", 1)
            stall_section = (
                f"\n⚠️ STALL RILEVATO: Il contesto è rimasto immutato per {stall_count} cicli consecutivi.\n"
                f"Il sistema potrebbe essere bloccato. Proponi azioni di RECOVERY specifiche:\n"
                f"- Se coerenza φ è bassa: proponi 'inject_energy' o 'reset_neurons'\n"
                f"- Se il tick è fermo: proponi 'restart_tick' o 'force_advance_tick'\n"
                f"- Se i neuroni sono inattivi: proponi 'activate_stalled_neurons'\n"
                f"Non ripetere le stesse analisi — proponi azioni DIVERSE dal ciclo precedente.\n"
            )

        if is_supervisor:
            prompt = (
                f"Sei il supervisor {self.name} ({self.agent_id}).\n"
                f"IL TUO RUOLO: Analizzare lo stato di SPEACE, identificare anomalie e problemi, "
                f"e proporre azioni correttive CONCRETE che i tuoi technician eseguiranno.\n\n"
                f"Ecco le azioni che puoi proporre:\n{catalog_summary}\n\n"
                f"Contesto attuale di SPEACE:{metrics_section}\n{context_str}\n"
                f"{stall_section}\n"
                f"ISTRUZIONI:\n"
                f"1. Identifica problemi specifici nel tuo dominio (coerenza bassa, energia insufficiente, parametri fuori range)\n"
                f"2. Per ogni problema, proponi UN'AZIONE CONCRETA dal tuo catalogo\n"
                f"3. Per file .py, il campo 'new_value' deve contenere il codice sorgente Python completo\n"
                f"4. Per file YAML, il campo 'new_value' deve essere un dict con le modifiche da applicare\n"
                f"5. Per parametri runtime, specifica il valore numerico o booleano\n"
                f"6. La 'justification' deve includere i valori metrici che motivano l'azione\n\n"
                f"Rispondi SOLO con un array JSON:\n"
                f'```json\n'
                f'[{{"action_type": "...", "target": "...", "new_value": ..., '
                f'"operation": "set|scale|enable|disable|write", "justification": "..."}}]\n'
                f'```\n'
                f"Sii SPECIFICO: usa solo target e action_type dal tuo catalogo.\n"
                f"Non inventare azioni non autorizzate.\n"
                f"Prioritizza azioni che risolvono le anomalie più critiche."
            )
        else:
            prompt = (
                f"Sei l'agente tecnico {self.name} ({self.agent_id}).\n"
                f"Ecco le azioni che puoi proporre:\n{catalog_summary}\n\n"
                f"Contesto attuale di SPEACE:{metrics_section}\n{context_str}\n\n"
                f"Analizza il contesto e proponi azioni concrete per migliorare lo stato del sistema.\n"
                f"Rispondi SOLO con un array JSON di proposte nel formato:\n"
                f'```json\n'
                f'[{{"action_type": "...", "target": "...", "new_value": ..., '
                f'"operation": "set|scale|enable|disable|write", "justification": "..."}}]\n'
                f'```\n'
                f"Sii specifico: usa solo target e action_type dal tuo catalogo. "
                f"Non inventare azioni non autorizzate."
            )

        response = self.chat(prompt)

        # If the LLM call failed, don't try to parse error messages as JSON
        if response.startswith("ERRORE:"):
            _logger.warning("Agent %s LLM call failed, skipping action proposal: %s", self.agent_id, response[:100])
            return []

        proposals = self._parse_action_proposals(response)

        # Filter to authorized proposals only
        authorized = []
        for p in proposals:
            if self.action_catalog.is_authorized(self.agent_id, p.action_category, p.target):
                authorized.append(p)
            else:
                _logger.warning(
                    "Agent %s proposed unauthorized action %s:%s — filtered out",
                    self.agent_id, p.action_category, p.target,
                )
        return authorized

    def _parse_action_proposals(self, response: str) -> List[ActionProposal]:
        """Parse action proposals from LLM response text.

        Looks for a JSON array in the response (possibly wrapped in ```json blocks).
        """
        proposals = []

        # Try to extract JSON from code blocks
        json_str = response
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()

        try:
            items = json.loads(json_str)
            if not isinstance(items, list):
                items = [items]
        except (json.JSONDecodeError, ValueError):
            _logger.debug("Could not parse LLM response as JSON for action proposals")
            return proposals

        for item in items:
            if not isinstance(item, dict):
                continue
            action_type = item.get("action_type", "")
            target = item.get("target", "")
            if not action_type or not target:
                continue

            category = self.action_catalog.infer_category(action_type, target)
            risk_level = self.action_catalog.get_risk_level(self.agent_id, category, target)

            proposal = ActionProposal(
                agent_id=self.agent_id,
                action_type=action_type,
                action_category=category,
                target=target,
                operation=item.get("operation", "set"),
                old_value=None,
                new_value=item.get("new_value"),
                risk_level=risk_level,
                justification=item.get("justification", ""),
                evidence={},
            )
            proposals.append(proposal)

        return proposals
