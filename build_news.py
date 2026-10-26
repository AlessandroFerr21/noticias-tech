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
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Radar Tech</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Newsreader:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#F5F6F8;--card:#fff;--ink:#141E27;--mut:#586775;--line:#DDE3E8;--acc:#0B6E8A;--chip:#E6ECF0;--r:14px;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0C151C;--card:#132029;--ink:#E8EEF2;--mut:#92A2AF;--line:#22333F;--acc:#5CC0DC;--chip:#182833}}
:root[data-theme="dark"]{--bg:#0C151C;--card:#132029;--ink:#E8EEF2;--mut:#92A2AF;--line:#22333F;--acc:#5CC0DC;--chip:#182833}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "DM Sans",system-ui,sans-serif}
a{color:inherit;text-decoration:none}
.wrap{max-width:1120px;margin:0 auto;padding:44px 24px 72px}
h1{font:500 3.2rem/1 "Newsreader",Georgia,serif;letter-spacing:-.02em;margin:0 0 10px}
.sub{color:var(--mut);margin:0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0 32px}
.chip{border:0;background:var(--chip);color:var(--ink);font:inherit;font-size:.9rem;padding:7px 15px;border-radius:999px;cursor:pointer}
.chip.on{background:var(--acc);color:#fff}
.chip:focus-visible,a:focus-visible,.mais:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
.thumb{display:block;position:relative;aspect-ratio:16/9;overflow:hidden;background:linear-gradient(135deg,hsl(var(--h) 45% 36%),hsl(var(--h) 55% 20%))}
.thumb span{position:absolute;left:16px;bottom:12px;font:500 1.15rem "Newsreader",Georgia,serif;color:#fff;opacity:.85}
.thumb img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#0003}
.meta{display:flex;gap:12px;font-size:.84rem;color:var(--mut);margin-bottom:6px}
.fonte{color:var(--acc);font-weight:600}
h2,h3{font-family:"Newsreader",Georgia,serif;font-weight:500;margin:0}
h2{font-size:2.1rem;line-height:1.15}
h3{font-size:1.25rem;line-height:1.28}
a:hover h2,h2 a:hover,h3 a:hover{text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:3px}
.corpo p{margin:10px 0 0;color:var(--mut);font-size:.96rem}
.destaque{display:grid;grid-template-columns:1.7fr 1fr;gap:32px;margin-bottom:48px}
.destaque[hidden],.card[hidden],.mais[hidden]{display:none}
.hero .thumb{border-radius:var(--r);margin-bottom:18px}
.laterais{border-top:1px solid var(--line)}
.lat{padding:18px 0;border-bottom:1px solid var(--line)}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;display:flex;flex-direction:column}
.card .corpo{padding:16px 18px 20px}
.mais{display:block;margin:36px auto 0;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-weight:500;padding:12px 26px;border-radius:999px;cursor:pointer}
.mais:hover{border-color:var(--acc);color:var(--acc)}
.vazio{color:var(--mut)}
footer{margin-top:48px;color:var(--mut);font-size:.85rem}
@media (max-width:820px){.destaque{grid-template-columns:1fr;gap:20px}h1{font-size:2.5rem}h2{font-size:1.7rem}.wrap{padding:32px 18px 56px}}
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>Radar Tech</h1>
<p class="sub">Prévia com notícias de exemplo. 22 notícias das últimas 72 horas. Atualizado em 26 de out às 10:42.</p>
<div class="chips" role="group" aria-label="Filtrar por fonte"><button class="chip on" data-fonte="">Todas</button><button class="chip" data-fonte="Ars Technica">Ars Technica</button><button class="chip" data-fonte="Canaltech">Canaltech</button><button class="chip" data-fonte="Hacker News">Hacker News</button><button class="chip" data-fonte="Olhar Digital">Olhar Digital</button><button class="chip" data-fonte="TechCrunch">TechCrunch</button><button class="chip" data-fonte="Tecnoblog">Tecnoblog</button><button class="chip" data-fonte="The Verge">The Verge</button></div>
</header>
<main>
<section class="destaque">
<div><article class="hero"><a class="thumb grande" style="--h:200" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Tecnoblog</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%2332cc7f&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%2320616e&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Tecnoblog</span><time>Hoje, 10:38</time></div><h2><a href="#" target="_blank" rel="noopener noreferrer">Nova geração de chips promete dobrar a autonomia de notebooks</a></h2><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article></div>
<div class="laterais"><article class="lat"><div class="meta"><span class="fonte">Canaltech</span><time>Hoje, 10:03</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Startup brasileira lança assistente de voz para atendimento bancário</a></h3></article><article class="lat"><div class="meta"><span class="fonte">Olhar Digital</span><time>Hoje, 09:28</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Atualização do sistema corrige falha de segurança em milhões de celulares</a></h3></article><article class="lat"><div class="meta"><span class="fonte">The Verge</span><time>Hoje, 08:53</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Como a computação em nuvem está mudando o trabalho das escolas</a></h3></article></div>
</section>
<section class="grade">
<article class="card" data-fonte="Tecnoblog" data-dest="1" hidden><a class="thumb" style="--h:200" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Tecnoblog</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%2332cc7f&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%2320616e&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Tecnoblog</span><time>Hoje, 10:38</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Nova geração de chips promete dobrar a autonomia de notebooks</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Canaltech" data-dest="1" hidden><a class="thumb" style="--h:160" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Canaltech</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%2332ccaa&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%23204b6e&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Canaltech</span><time>Hoje, 10:03</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Startup brasileira lança assistente de voz para atendimento bancário</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Olhar Digital" data-dest="1" hidden><a class="thumb" style="--h:260" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Olhar Digital</span></a><div class="corpo"><div class="meta"><span class="fonte">Olhar Digital</span><time>Hoje, 09:28</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Atualização do sistema corrige falha de segurança em milhões de celulares</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="The Verge" data-dest="1" hidden><a class="thumb" style="--h:220" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>The Verge</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%233296cc&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%2321206e&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">The Verge</span><time>Hoje, 08:53</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Como a computação em nuvem está mudando o trabalho das escolas</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="TechCrunch" data-dest="0"><a class="thumb" style="--h:180" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>TechCrunch</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%23326bcc&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%2337206e&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">TechCrunch</span><time>Hoje, 08:18</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Fabricante anuncia fone com cancelamento de ruído mais barato do ano</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Ars Technica" data-dest="0"><a class="thumb" style="--h:280" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Ars Technica</span></a><div class="corpo"><div class="meta"><span class="fonte">Ars Technica</span><time>Hoje, 07:43</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Pesquisadores criam bateria que carrega em menos de cinco minutos</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Hacker News" data-dest="0"><a class="thumb" style="--h:240" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Hacker News</span></a><div class="corpo"><div class="meta"><span class="fonte">Hacker News</span><time>Hoje, 07:08</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Ferramenta de código aberto simplifica a análise de dados em planilhas</a></h3></div></article>
<article class="card" data-fonte="Tecnoblog" data-dest="0"><a class="thumb" style="--h:200" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Tecnoblog</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%237c32cc&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%236e2062&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Tecnoblog</span><time>Hoje, 06:33</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Rede social testa recurso de resumo automático de conversas</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Canaltech" data-dest="0"><a class="thumb" style="--h:160" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Canaltech</span></a><div class="corpo"><div class="meta"><span class="fonte">Canaltech</span><time>Hoje, 05:58</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Smartwatch ganha novo sensor e amplia o monitoramento de atividades</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Olhar Digital" data-dest="0"><a class="thumb" style="--h:260" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Olhar Digital</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%23cc32c4&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%236e2036&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Olhar Digital</span><time>Hoje, 05:23</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Vulnerabilidade em roteadores domésticos preocupa especialistas</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="The Verge" data-dest="0"><a class="thumb" style="--h:220" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>The Verge</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%23cc3298&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%236e2020&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">The Verge</span><time>Hoje, 04:48</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Empresa mostra robô de limpeza que aprende a rotina da casa</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="TechCrunch" data-dest="0"><a class="thumb" style="--h:180" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>TechCrunch</span></a><div class="corpo"><div class="meta"><span class="fonte">TechCrunch</span><time>Hoje, 04:13</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Novo navegador chega com foco em privacidade e menos consumo de memória</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Ars Technica" data-dest="0"><a class="thumb" style="--h:280" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Ars Technica</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%23cc3242&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%236e4c20&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Ars Technica</span><time>Hoje, 03:38</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Console portátil recebe atualização e melhora desempenho em jogos</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Hacker News" data-dest="0"><a class="thumb" style="--h:240" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Hacker News</span></a><div class="corpo"><div class="meta"><span class="fonte">Hacker News</span><time>Hoje, 03:03</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Lançamento de satélite amplia a cobertura de internet em áreas remotas</a></h3></div></article>
<article class="card" data-fonte="Tecnoblog" data-dest="0"><a class="thumb" style="--h:200" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Tecnoblog</span></a><div class="corpo"><div class="meta"><span class="fonte">Tecnoblog</span><time>Hoje, 02:28</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Dev publica guia gratuito sobre bancos de dados para iniciantes</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Canaltech" data-dest="0"><a class="thumb" style="--h:160" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Canaltech</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%23cca532&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%234d6e20&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Canaltech</span><time>Hoje, 01:53</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Marketplace de apps muda regras de pagamento e gera debate</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Olhar Digital" data-dest="0"><a class="thumb" style="--h:260" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Olhar Digital</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%23c6cc32&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%23376e20&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Olhar Digital</span><time>Hoje, 01:18</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Câmera de celular ganha modo noturno com inteligência artificial</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="The Verge" data-dest="0"><a class="thumb" style="--h:220" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>The Verge</span></a><div class="corpo"><div class="meta"><span class="fonte">The Verge</span><time>Hoje, 00:43</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Plataforma de streaming prepara plano com anúncios mais barato</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="TechCrunch" data-dest="0"><a class="thumb" style="--h:180" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>TechCrunch</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%2370cc32&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%23206e35&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">TechCrunch</span><time>Hoje, 00:08</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Teclado mecânico compacto entra em pré-venda no Brasil</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Ars Technica" data-dest="0"><a class="thumb" style="--h:280" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Ars Technica</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%2344cc32&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%23206e4b&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Ars Technica</span><time>Ontem, 23:33</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Empresas de tecnologia anunciam parceria para padronizar carregadores</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
<article class="card" data-fonte="Hacker News" data-dest="0"><a class="thumb" style="--h:240" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Hacker News</span></a><div class="corpo"><div class="meta"><span class="fonte">Hacker News</span><time>Ontem, 22:58</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Estudo mostra crescimento do uso de dashboards em pequenas empresas</a></h3></div></article>
<article class="card" data-fonte="Tecnoblog" data-dest="0"><a class="thumb" style="--h:200" href="#" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true"><span>Tecnoblog</span><img src="data:image/svg+xml;utf8,&lt;svg xmlns=&#x27;http://www.w3.org/2000/svg&#x27; viewBox=&#x27;0 0 640 360&#x27;&gt;&lt;defs&gt;&lt;linearGradient id=&#x27;g&#x27; x1=&#x27;0&#x27; y1=&#x27;0&#x27; x2=&#x27;1&#x27; y2=&#x27;1&#x27;&gt;&lt;stop offset=&#x27;0&#x27; stop-color=&#x27;%2332cc77&#x27;/&gt;&lt;stop offset=&#x27;1&#x27; stop-color=&#x27;%2320656e&#x27;/&gt;&lt;/linearGradient&gt;&lt;/defs&gt;&lt;rect width=&#x27;640&#x27; height=&#x27;360&#x27; fill=&#x27;url(%23g)&#x27;/&gt;&lt;circle cx=&#x27;480&#x27; cy=&#x27;110&#x27; r=&#x27;90&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.18&#x27;/&gt;&lt;circle cx=&#x27;200&#x27; cy=&#x27;260&#x27; r=&#x27;140&#x27; fill=&#x27;white&#x27; fill-opacity=&#x27;.1&#x27;/&gt;&lt;/svg&gt;" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"></a><div class="corpo"><div class="meta"><span class="fonte">Tecnoblog</span><time>Ontem, 22:23</time></div><h3><a href="#" target="_blank" rel="noopener noreferrer">Impressora 3D doméstica chega com preço mais acessível</a></h3><p>Resumo curto de exemplo para mostrar como o texto aparece abaixo do título em cada cartão.</p></div></article>
</section>
<button class="mais" id="mais" type="button">Ver mais notícias</button>
</main>
<footer>Os títulos levam ao site original de cada fonte.</footer>
</div>
<script>
(function(){
  var PAGINA=12, filtro="", n=PAGINA;
  var cards=[].slice.call(document.querySelectorAll(".grade .card"));
  var destaque=document.querySelector(".destaque");
  var mais=document.getElementById("mais");
  function render(){
    var vis=cards.filter(function(c){
      return filtro===""?c.dataset.dest!=="1":c.dataset.fonte===filtro;
    });
    cards.forEach(function(c){c.hidden=true;});
    vis.forEach(function(c,i){c.hidden=i>=n;});
    destaque.hidden=filtro!=="";
    mais.hidden=vis.length<=n;
    mais.textContent="Ver mais notícias ("+(vis.length-n)+")";
  }
  document.querySelectorAll(".chip").forEach(function(b){
    b.addEventListener("click",function(){
      document.querySelectorAll(".chip").forEach(function(c){c.classList.remove("on");});
      b.classList.add("on");
      filtro=b.dataset.fonte; n=PAGINA; render();
    });
  });
  mais.addEventListener("click",function(){n+=PAGINA; render();});
  render();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    noticias = coletar()
    with open("index.html", "w", encoding="utf-8") as arquivo:
        arquivo.write(montar_html(noticias))
    print(f"index.html gerado com {len(noticias)} notícias")
