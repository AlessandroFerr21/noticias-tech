"""Gera o index.html com as notícias de tecnologia mais recentes (via RSS).

Para trocar as fontes, edite o dicionário FEEDS logo abaixo.
"""
import html
import re
from datetime import datetime, timedelta, timezone
from time import mktime
from zoneinfo import ZoneInfo

import feedparser

FEEDS = {
    "Tecnoblog": "https://tecnoblog.net/feed/",
    "Canaltech": "https://canaltech.com.br/rss/",
    "Olhar Digital": "https://olhardigital.com.br/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Hacker News": "https://hnrss.org/frontpage",
}

POR_FONTE = 12   # máximo de notícias por fonte
MAX_HORAS = 72   # ignora notícias mais antigas que isso
FUSO = ZoneInfo("America/Sao_Paulo")
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def limpar(texto, limite=200):
    """Tira HTML do resumo e corta no limite de caracteres."""
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = html.unescape(re.sub(r"\s+", " ", texto)).strip()
    if len(texto) > limite:
        texto = texto[:limite].rsplit(" ", 1)[0] + "…"
    return texto


def data_da_entrada(entrada):
    tempo = entrada.get("published_parsed") or entrada.get("updated_parsed")
    if not tempo:
        return None
    return datetime.fromtimestamp(mktime(tempo), tz=timezone.utc)


def coletar():
    limite = datetime.now(timezone.utc) - timedelta(hours=MAX_HORAS)
    itens = []
    for fonte, url in FEEDS.items():
        try:
            feed = feedparser.parse(url, agent="Mozilla/5.0 (noticias-tech bot)")
        except Exception as erro:
            print(f"[aviso] {fonte}: {erro}")
            continue
        if not feed.entries:
            print(f"[aviso] {fonte}: nenhuma notícia lida")
            continue
        for e in feed.entries[:POR_FONTE]:
            quando = data_da_entrada(e)
            link = e.get("link", "")
            if not quando or quando < limite or not link.startswith(("http://", "https://")):
                continue
            resumo = "" if fonte == "Hacker News" else limpar(e.get("summary", ""))
            itens.append({
                "fonte": fonte,
                "titulo": limpar(e.get("title", "(sem título)"), 160),
                "link": link,
                "resumo": resumo,
                "quando": quando.astimezone(FUSO),
            })
    itens.sort(key=lambda i: i["quando"], reverse=True)
    return itens


def rotulo_dia(dia, hoje):
    if dia == hoje:
        return "Hoje"
    if dia == hoje - timedelta(days=1):
        return "Ontem"
    return f"{DIAS[dia.weekday()].capitalize()}, {dia.day} de {MESES[dia.month - 1]}"


def montar_html(itens):
    agora = datetime.now(FUSO)
    hoje = agora.date()
    esc = html.escape

    fontes = sorted({i["fonte"] for i in itens})
    chips = '<button class="chip on" data-fonte="">Todas</button>' + "".join(
        f'<button class="chip" data-fonte="{esc(f)}">{esc(f)}</button>' for f in fontes
    )

    blocos, dia_atual = [], None
    for i in itens:
        dia = i["quando"].date()
        if dia != dia_atual:
            if dia_atual is not None:
                blocos.append("</section>")
            blocos.append(f'<section class="dia"><h2>{esc(rotulo_dia(dia, hoje))}</h2>')
            dia_atual = dia
        resumo = f'<p>{esc(i["resumo"])}</p>' if i["resumo"] else ""
        blocos.append(
            f'<article data-fonte="{esc(i["fonte"])}">'
            f'<div class="meta"><span class="fonte">{esc(i["fonte"])}</span>'
            f'<time>{i["quando"].strftime("%H:%M")}</time></div>'
            f'<h3><a href="{esc(i["link"])}" target="_blank" rel="noopener noreferrer">{esc(i["titulo"])}</a></h3>'
            f"{resumo}</article>"
        )
    if dia_atual is not None:
        blocos.append("</section>")
    if not itens:
        blocos.append('<p class="vazio">Nenhuma notícia carregada agora. A próxima atualização corrige isso.</p>')

    atualizado = f"{agora.day} de {MESES[agora.month - 1]} às {agora.strftime('%H:%M')}"
    return (TEMPLATE
            .replace("__CHIPS__", chips)
            .replace("__CONTEUDO__", "\n".join(blocos))
            .replace("__ATUALIZADO__", atualizado)
            .replace("__TOTAL__", str(len(itens))))


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar Tech</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#F2F5F7;--ink:#14202B;--mut:#5A6A77;--line:#D3DCE3;--acc:#0B6E8A;--chip:#E3EAEF}
@media (prefers-color-scheme:dark){:root{--bg:#0F1A22;--ink:#E7EEF3;--mut:#93A3B0;--line:#243541;--acc:#5CC0DC;--chip:#1A2A35}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 "Source Sans 3",system-ui,sans-serif}
.wrap{max-width:740px;margin:0 auto;padding:40px 20px 80px}
header{margin-bottom:28px}
h1{font:700 2.6rem/1.05 "Bricolage Grotesque",system-ui,sans-serif;margin:0 0 8px;letter-spacing:-.02em}
.sub{color:var(--mut);margin:0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 8px}
.chip{border:0;background:var(--chip);color:var(--ink);font:inherit;font-size:.9rem;padding:6px 14px;border-radius:999px;cursor:pointer}
.chip.on{background:var(--acc);color:#fff}
.chip:focus-visible,a:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
.dia h2{font:600 1rem/1 "Source Sans 3",sans-serif;color:var(--mut);margin:36px 0 4px;padding-bottom:10px;border-bottom:2px solid var(--ink)}
article{padding:18px 0;border-bottom:1px solid var(--line)}
article[hidden]{display:none}
.meta{display:flex;gap:12px;font-size:.85rem;color:var(--mut);margin-bottom:4px}
.fonte{color:var(--acc);font-weight:600}
h3{font:600 1.3rem/1.25 "Bricolage Grotesque",system-ui,sans-serif;margin:0}
h3 a{color:inherit;text-decoration:none}
h3 a:hover{text-decoration:underline;text-decoration-color:var(--acc);text-underline-offset:3px}
article p{margin:8px 0 0;color:var(--mut);font-size:.98rem}
.vazio{color:var(--mut);margin-top:40px}
footer{margin-top:40px;color:var(--mut);font-size:.85rem}
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>Radar Tech</h1>
<p class="sub">__TOTAL__ notícias das últimas 72 horas. Atualizado em __ATUALIZADO__.</p>
<div class="chips" role="group" aria-label="Filtrar por fonte">__CHIPS__</div>
</header>
<main>
__CONTEUDO__
</main>
<footer>Os títulos levam ao site original de cada fonte.</footer>
</div>
<script>
document.querySelectorAll('.chip').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('.chip').forEach(function(c){c.classList.remove('on')});
    b.classList.add('on');
    var f=b.dataset.fonte;
    document.querySelectorAll('article').forEach(function(a){
      a.hidden = f && a.dataset.fonte!==f;
    });
    document.querySelectorAll('.dia').forEach(function(d){
      d.hidden = !d.querySelector('article:not([hidden])');
    });
  });
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    noticias = coletar()
    with open("index.html", "w", encoding="utf-8") as arquivo:
        arquivo.write(montar_html(noticias))
    print(f"index.html gerado com {len(noticias)} notícias")
