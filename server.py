"""
Servidor Local de Estudos Bíblicos & Devocionais
Permite acesso no Desktop, no Celular (mesmo Wi-Fi) e fora de casa (via 4G com Tailscale ou Cloudflare Tunnel).
Uso:
    python server.py
"""

import http.server
import socket
import socketserver
import os
import re
import urllib.parse
from pathlib import Path

PORT = 8000
BASE_DIR = Path(__file__).resolve().parent

def get_local_ip():
    """Obtém o endereço IP local na rede Wi-Fi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não precisa conectar de verdade, apenas descobre a interface de rede ativa
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def scan_studies():
    """Escaneia a pasta Pregações e descobre todos os arquivos HTML de estudos."""
    pregacoes_dir = BASE_DIR / "Pregações"
    studies = []
    if not pregacoes_dir.exists():
        return studies

    for folder in sorted(pregacoes_dir.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        html_files = list(folder.glob("*.html"))
        for html_file in html_files:
            rel_path = html_file.relative_to(BASE_DIR).as_posix()
            url_path = urllib.parse.quote(rel_path)
            
            # Tenta extrair o título e meta do HTML
            title = folder.name
            badge = "Estudo Bíblico"
            summary = "Estudo pastoral e exegético."
            
            try:
                content = html_file.read_text(encoding="utf-8", errors="ignore")
                title_match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.DOTALL | re.IGNORECASE)
                if title_match:
                    clean_title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
                    if clean_title and not clean_title.startswith("["):
                        title = clean_title
                
                if "Devocional" in folder.name or "Devocional" in content:
                    badge = "Devocional Rápido"
                elif "Exegese" in content or "Homilética" in content:
                    badge = "Estudo Exegético & Sermão"

                lead_match = re.search(r'class="hero-lead"[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
                if not lead_match:
                    lead_match = re.search(r'class="section-lead"[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
                if lead_match:
                    clean_lead = re.sub(r"<[^>]+>", "", lead_match.group(1)).strip()
                    if clean_lead and not clean_lead.startswith("["):
                        summary = clean_lead[:140] + "..."
            except Exception:
                pass

            studies.append({
                "folder": folder.name,
                "title": title,
                "badge": badge,
                "summary": summary,
                "url": url_path,
                "filename": html_file.name
            })
    return studies

def generate_index_html():
    """Gera automaticamente um index.html dinâmico e responsivo com os estudos disponíveis."""
    studies = scan_studies()
    
    cards_html = ""
    for s in studies:
        badge_style = 'style="border-left-color: var(--rust-dark);"' if "Devocional" in s["badge"] else ''
        cards_html += f"""
      <a class="card" {badge_style} href="{s['url']}">
        <span class="card-badge">{s['badge']} · {s['folder'].split(' - ')[1] if ' - ' in s['folder'] else s['folder']}</span>
        <h2>{s['title']}</h2>
        <p>{s['summary']}</p>
      </a>"""

    if not cards_html:
        cards_html = """
      <div class="card" style="border-left-color: var(--gold);">
        <span class="card-badge">Nenhum estudo encontrado</span>
        <h2>Pasta Pregações vazia</h2>
        <p>Crie uma nova pasta em Pregações/ com o template desejado.</p>
      </div>"""

    index_content = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#20372a">
  <title>Biblioteca de Estudos Bíblicos & Devocionais</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Newsreader:ital,opsz,wght@0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f3f0e8;
      --paper: #fffdf8;
      --ink: #16201c;
      --muted: #47544d;
      --forest: #30493a;
      --forest-2: #20372a;
      --rust: #a64d2e;
      --rust-dark: #8c3b20;
      --gold: #b68a43;
      --line: #c9c8bd;
      --reading-size: 17px;
      --page: 760px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 400 var(--reading-size)/1.6 "DM Sans", system-ui, -apple-system, sans-serif;
      padding: 24px 18px 80px;
    }}
    .wrapper {{
      max-width: var(--page);
      margin: 0 auto;
    }}
    header {{
      padding-bottom: 20px;
      border-bottom: 2px solid var(--line);
      margin-bottom: 28px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
    }}
    .kicker {{
      color: var(--rust-dark);
      font-size: .78rem;
      font-weight: 700;
      letter-spacing: .15em;
      text-transform: uppercase;
      margin: 0 0 6px;
    }}
    h1 {{
      font: 700 clamp(1.8rem, 4vw, 2.3rem)/1.15 "Newsreader", Georgia, serif;
      margin: 0;
      color: var(--forest-2);
    }}
    .templates-nav {{
      font-size: .8rem;
      font-weight: 600;
      color: var(--muted);
    }}
    .templates-nav a {{
      color: var(--forest);
      text-decoration: none;
      padding: 4px 8px;
      border: 1px solid var(--line);
      background: var(--paper);
      border-radius: 4px;
    }}
    .list {{
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .card {{
      display: block;
      padding: 20px 22px;
      background: var(--paper);
      border: 1px solid var(--line);
      border-left: 5px solid var(--forest);
      text-decoration: none;
      color: inherit;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(22, 32, 28, .03);
      transition: transform .12s ease, box-shadow .12s ease;
    }}
    .card:active {{
      transform: scale(0.99);
      background: #f8f5ee;
    }}
    .card-badge {{
      display: inline-block;
      font-size: .72rem;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--rust-dark);
      margin-bottom: 6px;
    }}
    .card h2 {{
      font: 600 1.3rem "Newsreader", Georgia, serif;
      margin: 0 0 6px;
      color: var(--ink);
      line-height: 1.25;
    }}
    .card p {{
      margin: 0;
      font-size: .9rem;
      color: var(--muted);
      line-height: 1.5;
    }}
    footer {{
      margin-top: 48px;
      padding-top: 20px;
      border-top: 1px solid var(--line);
      font-size: .8rem;
      color: var(--muted);
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <header>
      <div>
        <p class="kicker">Biblioteca Pastoral</p>
        <h1>Estudos Bíblicos &amp; Devocionais</h1>
      </div>
      <div class="templates-nav">
        <a href="templates/TEMPLATE-ESTUDO-EXEGETICO.html">Modelo Exegético</a>
        <a href="templates/TEMPLATE-DEVOCIONAL.html">Modelo Devocional</a>
      </div>
    </header>

    <div class="list">
{cards_html}
    </div>

    <footer>
      Servidor Local · Acesso pessoal Desktop & Mobile (Wi-Fi e 4G).
    </footer>
  </div>
</body>
</html>
"""
    (BASE_DIR / "index.html").write_text(index_content, encoding="utf-8")

class UTF8HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP customizado com charset UTF-8 forçado e atualização automática de índice."""
    
    def end_headers(self):
        # Garante UTF-8 para todos os arquivos HTML/texto
        if self.path.endswith(".html") or self.path == "/" or self.path == "":
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            generate_index_html()
        super().do_GET()

def main():
    os.chdir(BASE_DIR)
    generate_index_html()
    local_ip = get_local_ip()

    print("=" * 65)
    print(" 📖 SERVIDOR DE ESTUDOS BÍBLICOS & DEVOCIONAIS INICIADO")
    print("=" * 65)
    print(f"\n 💻 No Computador (Local):")
    print(f"    http://localhost:{PORT}")
    print(f"\n 📱 No Celular (Mesmo Wi-Fi da sua casa):")
    print(f"    http://{local_ip}:{PORT}")
    print(f"\n 🌐 Fora de Casa (Via 4G / Internet Externa):")
    print(f"    Opção 1 (Recomendada): Use o app Tailscale no PC e no Celular.")
    print(f"    Opção 2 (Túnel Cloudflare): Execute em outro terminal:")
    print(f"       cloudflared tunnel --url http://localhost:{PORT}")
    print("\n Pressione Ctrl+C para encerrar o servidor.")
    print("=" * 65 + "\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), UTF8HttpRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")

if __name__ == "__main__":
    main()
