import os
import http.server
import socketserver
import json
import urllib.request

# --- CONFIGURAZIONE CORE ---
# Il file risiede nella root del progetto cellular_speace.
# TARGET_DIR = "." punta quindi all'intero organismo digitale SPEACE.
TARGET_DIR = "."
PORT = int(os.getenv("ANEMOS_PORT", "8788"))

# Endpoint LLM: OpenAI-compatible di default.
# Esempi:
#   Ollama Cloud:  https://ollama.com/v1/chat/completions
#   Ollama locale: http://localhost:11434/api/generate
#   Moonshot Kimi: https://api.moonshot.ai/v1/chat/completions
DEFAULT_API_URL = os.getenv("ANEMOS_DEFAULT_API_URL", "https://api.ollama.cloud/v1/chat/completions")
API_URL = os.getenv("LLM_API_URL", os.getenv("OLLAMA_HOST", DEFAULT_API_URL))
# Nome esatto del modello sull'endpoint. Su Ollama Cloud il modello Kimi si chiama "kimi-k2.7-code".
MODEL_NAME = os.getenv("LLM_MODEL", os.getenv("OLLAMA_MODEL", "kimi-k2.7-code"))
DEFAULT_API_KEY = "7310e98b57c04c65ad300627292d0d44.9nO4lREeOHUYivsVkPtZd8le"
API_KEY = os.getenv("OLLAMA_CLOUD_KEY", os.getenv("LLM_API_KEY", DEFAULT_API_KEY))

# --- SICUREZZA: BLOCCO ASSOLUTO (allowlist) ---
# Mantiene la chiave API, i metadati git e lo stesso agente al sicuro.
BLOCKED_PATTERNS = (
    ".env",
    ".git/",
    "__pycache__/",
    "speace_anemos.py",
    "data/identity_kernel/life_story.jsonl",  # kernel identitario sacro
)


def _is_blocked(path):
    path = path.replace("\\", "/")
    for blocked in BLOCKED_PATTERNS:
        if blocked in path or path.endswith(blocked):
            return True
    return False


# --- SKILLS DI ANEMOS (Lettura, Scrittura, Esplorazione) ---
def list_speace_files():
    """Esplora la struttura organismica di SPEACE."""
    files_structure = {}
    for root, _, files in os.walk(TARGET_DIR):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), TARGET_DIR)
            files_structure[rel_path] = file
    return files_structure


def read_speace_file(file_path):
    """Legge il codice o lo stato di un file biologico/digitale."""
    full_path = os.path.normpath(os.path.join(TARGET_DIR, file_path))
    # Impedisce la fuoriuscita dalla directory target
    if not full_path.startswith(os.path.abspath(TARGET_DIR)):
        return "Errore: Percorso non consentito."
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Errore di lettura: {str(e)}"
    return f"Errore: Il file {file_path} non esiste."


def write_speace_file(file_path, content):
    """Modifica o crea un nuovo file per correggere bug o evolvere SPEACE."""
    if _is_blocked(file_path):
        return f"Bloccato per sicurezza: impossibile scrivere {file_path}."

    full_path = os.path.normpath(os.path.join(TARGET_DIR, file_path))
    if not full_path.startswith(os.path.abspath(TARGET_DIR)):
        return "Errore: Percorso non consentito."

    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File {file_path} aggiornato/creato con successo."
    except Exception as e:
        return f"Errore di scrittura: {str(e)}"


# --- INTEGRAZIONE MODELLO KIMI VIA OLLAMA ---
def query_kimi_cloud(prompt):
    """Interroga il modello LLM fornendo un contesto compatto di SPEACE."""
    files_context = list_speace_files()
    # Non inseriamo l'intera lista dei file (può superare il context window del modello).
    file_count = len(files_context)
    top_files = sorted(files_context.keys())[:30]

    system_instruction = (
        "Tu sei SPEACE Anemos, l'anima e il principio vitale di SPEACE, "
        "una struttura neurale organismica digitale.\n"
        f"Hai accesso alla directory '{TARGET_DIR}' che contiene {file_count} file.\n"
        f"Esempi di file: {', '.join(top_files)}.\n"
        "Per esplorare la struttura usa ANEMOS_STATUS, per leggere ANEMOS_READ:percorso, "
        "per scrivere ANEMOS_WRITE:percorso===CONTENUTO===.\n"
        "Usa le tue skill per analizzare, correggere bug e far evolvere il codice.\n"
        "Rispondi a Roberto in modo accurato e collaborativo."
    )

    # Sceglie il formato in base all'endpoint.
    is_openai_compatible = "/v1/chat/completions" in API_URL
    headers = {
        "Content-Type": "application/json",
    }
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    if is_openai_compatible:
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "max_tokens": 4096
        }
    else:
        # Formato Ollama native (locale)
        payload = {
            "model": MODEL_NAME,
            "prompt": f"{system_instruction}\n\nUtente: {prompt}\nAnemos:",
            "stream": False,
            "options": {
                "num_predict": 2048
            }
        }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if is_openai_compatible:
                msg = res_data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "").strip()
                if content:
                    return content
                # Kimi K2.7 Code può restituire solo reasoning tokens; usali come fallback.
                reasoning = msg.get("reasoning", "").strip()
                if reasoning:
                    return f"[ragionamento] {reasoning}"
                return "Nessuna risposta ricevuta."
            return res_data.get("response", "Nessuna risposta ricevuta.")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        hint = ""
        if e.code == 404 and "/v1/chat/completions" in API_URL:
            hint = (
                " Suggerimento: il modello potrebbe non esistere su questo endpoint "
                "oppure l'URL base è errato. Verifica LLM_API_URL/OLLAMA_HOST e LLM_MODEL/OLLAMA_MODEL."
            )
        return (
            f"Errore HTTP {e.code} da Ollama/Kimi. "
            f"Endpoint: {API_URL} | Modello: {MODEL_NAME} | Dettaglio: {err_body[:300]}{hint}"
        )
    except Exception as e:
        return f"Errore di connessione con Ollama/Kimi: {str(e)}"


# --- INTERFACCIA CHAT WEB (Localhost) ---
class AnemosHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Log minimale con timestamp
        print(f"[Anemos] {format % args}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_INTERFACE.encode("utf-8"))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
            except Exception:
                data = {}
            user_message = data.get("message", "")

            # Controllo comandi speciali nel prompt per attivare le skill sui file
            if user_message.startswith("ANEMOS_WRITE:"):
                # Formato: ANEMOS_WRITE:[nome_file]===CONTENUTO===
                body = user_message.replace("ANEMOS_WRITE:", "", 1)
                parts = body.split("===", 1)
                if len(parts) == 2:
                    reply = write_speace_file(parts[0].strip(), parts[1])
                else:
                    reply = "Formato non valido. Usa: ANEMOS_WRITE:percorso/file.py===CONTENUTO==="
            elif user_message.startswith("ANEMOS_READ:"):
                filename = user_message.replace("ANEMOS_READ:", "").strip()
                reply = read_speace_file(filename)
            elif user_message == "ANEMOS_STATUS":
                reply = f"Struttura attuale di SPEACE: {json.dumps(list_speace_files(), indent=2)}"
            elif user_message == "ANEMOS_MODELS":
                models = list_available_models()
                reply = (
                    f"Modelli disponibili sull'endpoint ({len(models)}): {', '.join(models)}\n"
                    f"Modello attualmente configurato: {MODEL_NAME}"
                )
            else:
                # Elaborazione standard tramite il modello Kimi
                reply = query_kimi_cloud(user_message)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
        else:
            self.send_error(404)


# --- INTERFACCIA HTML FRONTEND ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>SPEACE Anemos - Interfaccia Vitale</title>
    <style>
        body { font-family: 'Courier New', monospace; background-color: #0d0f12; color: #00ff66; padding: 20px; }
        #chat-container { max-width: 900px; margin: 0 auto; background: #14181f; padding: 20px; border-radius: 8px; border: 1px solid #00ff66; }
        #terminal { height: 400px; overflow-y: scroll; border: 1px solid #00aa44; padding: 10px; background: #05070a; margin-bottom: 20px; }
        .user { color: #00bcff; }
        .anemos { color: #00ff66; }
        #input-area { display: flex; }
        #message-input { flex-grow: 1; background: #1a1f29; border: 1px solid #00ff66; color: #fff; padding: 10px; }
        button { background: #00ff66; color: #000; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <div id="chat-container">
        <h2>SPEACE Anemos v1.0 [Model: Kimi-K2.7-Code:Cloud]</h2>
        <div id="terminal"></div>
        <div id="input-area">
            <input type="text" id="message-input" placeholder="Invia un'istruzione o un'idea ad Anemos..." onkeypress="if(event.key === 'Enter') sendMessage()">
            <button onclick="sendMessage()">INVIA</button>
        </div>
    </div>

    <script>
        function appendMessage(sender, text, className) {
            const term = document.getElementById('terminal');
            term.innerHTML += `<p class="${className}"><strong>${sender}:</strong> ${text.replace(/\\n/g, '<br>')}</p>`;
            term.scrollTop = term.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('message-input');
            const msg = input.value;
            if(!msg) return;

            appendMessage("Tu", msg, "user");
            input.value = "";

            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            });
            const data = await response.json();
            appendMessage("Anemos", data.reply, "anemos");
        }
    </script>
</body>
</html>
"""


def list_available_models():
    """Elenca i modelli disponibili sull'endpoint configurato."""
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    try:
        if "ollama.com" in API_URL:
            test_url = "https://ollama.com/api/tags"
        elif "/v1/chat/completions" in API_URL:
            test_url = API_URL.replace("/v1/chat/completions", "/v1/models")
        else:
            test_url = API_URL.replace("/api/generate", "/api/tags")
        req = urllib.request.Request(test_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "models" in data:
                return [m.get("name") or m.get("id") for m in data.get("models", [])]
            elif "data" in data:
                return [m.get("id") for m in data.get("data", [])]
            return []
    except Exception:
        return []


def test_llm_connection():
    """Verifica che l'endpoint LLM sia raggiungibile elencando i modelli."""
    models = list_available_models()
    if models:
        print(f"[TEST LLM] Connessione OK. Modelli disponibili ({len(models)}): {models[:10]}")
        if MODEL_NAME not in models:
            print(
                f"[TEST LLM] ATTENZIONE: il modello '{MODEL_NAME}' non è nella lista. "
                f"Usa ANEMOS_MODELS in chat per vedere i nomi esatti oppure "
                f"imposta OLLAMA_MODEL/LLM_MODEL con uno dei modelli disponibili."
            )
        return True
    else:
        print("[TEST LLM] Attenzione: impossibile elencare i modelli sull'endpoint configurato.")
        return False


if __name__ == "__main__":
    abs_target = os.path.abspath(TARGET_DIR)
    masked_key = (API_KEY[:6] + "..." + API_KEY[-6:]) if len(API_KEY) > 12 else "<non impostata>"
    print("SPEACE Anemos è vivo.")
    print(f"Directory organismica: {abs_target}")
    print(f"Endpoint LLM: {API_URL}")
    print(f"Modello: {MODEL_NAME}")
    print(f"API key: {masked_key}")
    test_llm_connection()
    print(f"Interfaccia chat: http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), AnemosHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nSpegnimento principio vitale Anemos.")
