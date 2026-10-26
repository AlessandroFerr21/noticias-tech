"""Gera o index.html do Radar Tech com as notícias de tecnologia mais recentes (via RSS).

Para trocar as fontes, edite o dicionário FEEDS logo abaixo.
"""
import html
import re
import socket
from urllib.parse import quote_plus
from datetime import datetime, timedelta, timezone
from time import mktime
from zoneinfo import ZoneInfo

import feedparser


def google_news(busca):
    """Feed de notícias do Google News (em português) para uma busca."""
    return ("https://news.google.com/rss/search?q=" + quote_plus(busca)
            + "&hl=pt-BR&gl=BR&ceid=BR:pt-419")


FEEDS = {
    # Brasil
    "Tecnoblog": "https://tecnoblog.net/feed/",
    "Canaltech": "https://canaltech.com.br/rss/",
    "Olhar Digital": "https://olhardigital.com.br/feed/",
    "TecMundo": "https://rss.tecmundo.com.br/feed",
    "Meio Bit": "https://meiobit.com/feed/",
    "TechTudo": "https://www.techtudo.com.br/rss/techtudo/",
    "Showmetech": "https://www.showmetech.com.br/feed/",
    "Diolinux": "https://diolinux.com.br/feed",
    "Mobile Time": "https://www.mobiletime.com.br/feed/",
    "Computerworld": "https://computerworld.com.br/feed/",
    "Data Hackers": "https://medium.com/feed/data-hackers",
    "Google Brasil": "https://blog.google/intl/pt-br/rss/",
    # Internacional
    "Google Cloud": "https://blog.google/products/google-cloud/rss/",
    "DeepMind": "https://deepmind.google/blog/rss.xml",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Hacker News": "https://hnrss.org/frontpage",
    # Inteligência artificial (aparecem só nas abas IA e Dados / Google)
    "OpenAI": "https://openai.com/news/rss.xml",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "The Decoder": "https://the-decoder.com/feed/",
    "MIT Tech Review": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "Notícias Claude": google_news('"Anthropic" OR "Claude AI"'),
    "Notícias ChatGPT": google_news("OpenAI OR ChatGPT"),
    "Notícias Gemini": google_news('"Google Gemini" OR "Gemini AI"'),
    "Outras IAs": google_news("DeepSeek OR Grok OR Perplexity OR Copilot OR Mistral"),
}

# Fontes que só aparecem quando você abre uma categoria (não lotam a aba "Todas")
EXCLUSIVAS = {"OpenAI", "Hugging Face", "The Decoder", "MIT Tech Review", "DeepMind",
              "Notícias Claude", "Notícias ChatGPT", "Notícias Gemini", "Outras IAs"}

# Notícias de qualquer fonte que citem estes termos também entram em "IA e Dados"
IA_NOME = re.compile(r"claude|anthropic|openai|chatgpt|\bgpt-?\d|gemini|deepmind|copilot|llama|mistral"
                     r"|\bgrok\b|deepseek|perplexity|inteligência artificial|artificial intelligence", re.I)
IA_SIGLA = re.compile(r"\b(IA|AI|LLM|LLMs)\b")

# Categorias dos botões do topo (uma fonte pode estar em mais de uma)
CATEGORIAS = {
    "Brasil": ["Tecnoblog", "Canaltech", "Olhar Digital", "TecMundo", "Meio Bit", "TechTudo",
               "Showmetech", "Diolinux", "Mobile Time", "Computerworld", "Data Hackers", "Google Brasil"],
    "Internacional": ["The Verge", "TechCrunch", "Ars Technica", "Hacker News", "Google Cloud", "DeepMind",
                      "OpenAI", "Hugging Face", "The Decoder", "MIT Tech Review"],
    "IA e Dados": ["Data Hackers", "DeepMind", "Google Cloud", "OpenAI", "Hugging Face", "The Decoder",
                   "MIT Tech Review", "Notícias Claude", "Notícias ChatGPT", "Notícias Gemini", "Outras IAs"],
    "Google": ["Google Brasil", "Google Cloud", "DeepMind", "Notícias Gemini"],
}

POR_FONTE = 10   # máximo de notícias por fonte
MAX_HORAS = 72   # ignora notícias mais antigas que isso
socket.setdefaulttimeout(20)  # não fica esperando um site que não responde
FUSO = ZoneInfo("America/Sao_Paulo")
MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
MATIZES = [200, 160, 260, 220, 180, 280, 240, 170, 250, 210, 190, 270]  # cor de fundo de cada fonte


def texto(bruto):
    """Tira HTML e espaços repetidos."""
    t = re.sub(r"<[^>]+>", " ", bruto or "")
    return html.unescape(re.sub(r"\s+", " ", t)).strip()


def cortar(t, limite):
    if len(t) > limite:
        t = t[:limite].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"
    return t


def resumo_limpo(bruto, titulo):
    """Resumo curto, sem repetir o título (alguns feeds colam o título no resumo)."""
    r = texto(bruto)
    if titulo and r.endswith(titulo):
        r = r[: -len(titulo)].rstrip()
    if titulo and r.startswith(titulo):
        r = r[len(titulo):].lstrip(" -–:")
    return cortar(r, 170)


def url_ok(u):
    u = (u or "").strip()
    if u.startswith("//"):
        u = "https:" + u
    if u.startswith("http://"):
        u = "https://" + u[7:]
    if not u.startswith("https://"):
        return ""
    if re.search(r"pixel|tracking|doubleclick|feedburner|spacer", u, re.I):
        return ""
    return u


def imagem(e):
    """Procura a imagem da notícia nos lugares onde os feeds costumam colocá-la."""
    candidatos = []
    for m in list(e.get("media_content", [])) + list(e.get("media_thumbnail", [])):
        if m.get("medium", "image") == "image" and "video" not in m.get("type", ""):
            candidatos.append(m.get("url"))
    for enc in e.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            candidatos.append(enc.get("href") or enc.get("url"))
    for lk in e.get("links", []):
        if lk.get("type", "").startswith("image"):
            candidatos.append(lk.get("href"))
    blocos = [c.get("value", "") for c in e.get("content", [])] + [e.get("summary", "")]
    for b in blocos:
        achou = re.search(r'<img[^>]+src=["\']([^"\']+)', b or "")
        if achou:
            candidatos.append(achou.group(1))
    for c in candidatos:
        u = url_ok(c)
        if u:
            return u
    return ""


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
            titulo = texto(e.get("title", "")) or "(sem título)"
            resumo = "" if fonte == "Hacker News" else resumo_limpo(e.get("summary", ""), titulo)
            if url.startswith("https://news.google.com/") and " - " in titulo:
                titulo, _, veiculo = titulo.rpartition(" - ")
                resumo = f"Fonte: {veiculo}"
            eh_ia = bool(IA_NOME.search(f"{titulo} {resumo}") or IA_SIGLA.search(f"{titulo} {resumo}"))
            itens.append({
                "ia": eh_ia,
                "fonte": fonte,
                "titulo": cortar(titulo, 150),
                "link": link,
                "resumo": resumo,
                "imagem": imagem(e),
                "quando": quando.astimezone(FUSO),
            })
    itens.sort(key=lambda i: i["quando"], reverse=True)
    return itens


def quando_txt(dt, hoje):
    hora = dt.strftime("%H:%M")
    if dt.date() == hoje:
        return f"Hoje, {hora}"
    if dt.date() == hoje - timedelta(days=1):
        return f"Ontem, {hora}"
    return f"{dt.day} {MESES[dt.month - 1]}, {hora}"


def montar_html(itens):
    agora = datetime.now(FUSO)
    hoje = agora.date()
    esc = html.escape
    ordem = list(FEEDS)

    def matiz(fonte):
        pos = ordem.index(fonte) if fonte in ordem else 0
        return MATIZES[pos % len(MATIZES)]

    def thumb(i, classe="thumb"):
        img = (f'<img src="{esc(i["imagem"])}" alt="" loading="lazy" '
               f'referrerpolicy="no-referrer" onerror="this.remove()">') if i["imagem"] else ""
        return (f'<a class="{classe}" style="--h:{matiz(i["fonte"])}" href="{esc(i["link"])}" '
                f'target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true">'
                f'<span>{esc(i["fonte"])}</span>{img}</a>')

    def meta(i, com_fonte=True):
        fonte = f'<span class="fonte">{esc(i["fonte"])}</span>' if com_fonte else ""
        return f'<div class="meta">{fonte}<time>{esc(quando_txt(i["quando"], hoje))}</time></div>'

    def titulo(i, tag="h3"):
        return (f'<{tag}><a href="{esc(i["link"])}" target="_blank" '
                f'rel="noopener noreferrer">{esc(i["titulo"])}</a></{tag}>')

    def cats_item(i):
        cats = [nome for nome, lista in CATEGORIAS.items() if i["fonte"] in lista]
        if i["ia"] and "IA e Dados" not in cats:
            cats.append("IA e Dados")
        return cats

    def card(i, destaque):
        resumo = f'<p>{esc(i["resumo"])}</p>' if i["resumo"] else ""
        pill = f'<span class="pill">{esc(i["fonte"])}</span>' if i["imagem"] else ""
        oculto = " hidden" if destaque else ""
        return (f'<article class="card" data-fonte="{esc(i["fonte"])}" data-cats="{esc("|".join(cats_item(i)))}" '
                f'data-so="{1 if i["fonte"] in EXCLUSIVAS else 0}" data-dest="{1 if destaque else 0}"{oculto}>{pill}{thumb(i)}'
                f'<div class="corpo">{meta(i, False)}{titulo(i)}{resumo}</div></article>')

    presentes = {i["fonte"] for i in itens}
    abas = [f'<button class="aba on" role="tab" aria-selected="true" data-cat="" '
            f'data-fontes="{esc("|".join(sorted(presentes)))}">Todas</button>']
    for nome, lista in CATEGORIAS.items():
        fs = sorted({i["fonte"] for i in itens if nome in cats_item(i)})
        if fs:
            abas.append(f'<button class="aba" role="tab" aria-selected="false" data-cat="{esc(nome)}" '
                        f'data-fontes="{esc("|".join(fs))}">{esc(nome)}</button>')
    chips = "".join(abas)

    hero_html = laterais_html = grade_html = ""
    if itens:
        gerais = [i for i in itens if i["fonte"] not in EXCLUSIVAS] or itens
        hero = next((i for i in gerais if i["imagem"]), gerais[0])
        laterais, vistas = [], {hero["fonte"]}
        for i in gerais:
            if i is not hero and i["fonte"] not in vistas and len(laterais) < 3:
                laterais.append(i)
                vistas.add(i["fonte"])
        ids_dest = {id(hero)} | {id(i) for i in laterais}
        resumo = f'<p>{esc(hero["resumo"])}</p>' if hero["resumo"] else ""
        hero_html = (f'<article class="hero" style="--h:{matiz(hero["fonte"])}">{thumb(hero, "thumb fundo")}'
                     f'<div class="texto"><div class="meta"><span class="pill">{esc(hero["fonte"])}</span>'
                     f'<time>{esc(quando_txt(hero["quando"], hoje))}</time></div>'
                     f'{titulo(hero, "h2")}{resumo}</div></article>')
        laterais_html = "".join(
            f'<article class="lat"><span class="num">{n:02d}</span><div>{meta(i)}{titulo(i)}</div></article>'
            for n, i in enumerate(laterais, 1))
        grade_html = "\n".join(card(i, id(i) in ids_dest) for i in itens)
    else:
        grade_html = '<p class="vazio">Nenhuma notícia carregada agora. A próxima atualização corrige isso.</p>'

    atualizado = f"{agora.day} de {MESES[agora.month - 1]} às {agora.strftime('%H:%M')}"
    return (TEMPLATE
            .replace("__CHIPS__", chips)
            .replace("__HERO__", hero_html)
            .replace("__LATERAIS__", laterais_html)
            .replace("__GRADE__", grade_html)
            .replace("__ATUALIZADO__", atualizado)
            .replace("__TOTAL__", str(len(itens))))


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Radar Tech</title>
<script>
(function(){var d=document.documentElement;d.classList.add("js");var t=null;
try{t=localStorage.getItem("tema")}catch(e){}
if(t!=="light"&&t!=="dark"){t=window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}
d.dataset.theme=t;})();
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Pixelify+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#E7EEF8;--grid:rgba(26,28,44,.07);--card:#fff;--ink:#1A1C2C;--mut:#566C86;--borda:#1A1C2C;--acc:#3B5DC9;--acc2:#FFCD75;--num:#B13E53;--chip:#CFD9EA;--on-acc:#fff;
--sombra:6px 6px 0 #1A1C2C;--sombra-h:10px 10px 0 #1A1C2C;--pix:"Pixelify Sans",ui-monospace,monospace;--tit:"Press Start 2P","Courier New",monospace;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1A1C2C;--grid:rgba(244,244,244,.05);--card:#262B44;--ink:#F4F4F4;--mut:#94B0C2;--borda:#566C86;--acc:#73EFF7;--acc2:#FFCD75;--num:#EF7D57;--chip:#333C57;--on-acc:#1A1C2C;--sombra:6px 6px 0 #0B0C16;--sombra-h:10px 10px 0 #0B0C16}}
:root[data-theme="dark"]{--bg:#1A1C2C;--grid:rgba(244,244,244,.05);--card:#262B44;--ink:#F4F4F4;--mut:#94B0C2;--borda:#566C86;--acc:#73EFF7;--acc2:#FFCD75;--num:#EF7D57;--chip:#333C57;--on-acc:#1A1C2C;--sombra:6px 6px 0 #0B0C16;--sombra-h:10px 10px 0 #0B0C16;color-scheme:dark}
*{box-sizing:border-box;border-radius:0}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
body{margin:0;background-color:var(--bg);background-image:linear-gradient(var(--grid) 2px,transparent 2px),linear-gradient(90deg,var(--grid) 2px,transparent 2px);background-size:32px 32px;color:var(--ink);font:18px/1.45 var(--pix);transition:background-color .3s steps(4),color .3s steps(4)}
body::before{content:"";position:fixed;inset:0;z-index:200;pointer-events:none;background:repeating-linear-gradient(to bottom,rgba(0,0,0,.06) 0 2px,transparent 2px 4px)}
@keyframes subir{from{opacity:0;transform:translateY(24px)}}
@keyframes piscar{50%{opacity:0}}
a{color:inherit;text-decoration:none}
.progresso{position:fixed;top:0;left:0;right:0;height:10px;z-index:300;transform:scaleX(0);transform-origin:left;background:repeating-linear-gradient(90deg,var(--acc) 0 10px,transparent 10px 14px)}
.topo{position:sticky;top:env(safe-area-inset-top,0px);z-index:50;background:var(--card);border-bottom:4px solid var(--borda)}
.topo-in{max-width:1120px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
.logo{display:flex;align-items:center;gap:12px;font:400 .95rem var(--tit);text-transform:uppercase}
.ponto{width:14px;height:14px;background:var(--acc);animation:piscar 1s steps(1) infinite}
.tema{position:relative;width:46px;height:46px;border:4px solid var(--borda);background:var(--card);color:var(--ink);cursor:pointer;box-shadow:3px 3px 0 var(--borda);transition:transform .12s steps(2),box-shadow .12s steps(2)}
.tema:hover{transform:translate(-2px,-2px);box-shadow:5px 5px 0 var(--borda)}
.tema:active{transform:translate(3px,3px);box-shadow:0 0 0 var(--borda)}
.tema svg{position:absolute;inset:0;margin:auto;shape-rendering:crispEdges;transition:transform .2s steps(3),opacity .2s steps(3)}
:root[data-theme="dark"] .i-lua,:root:not([data-theme="dark"]) .i-sol{opacity:0;transform:scale(.4)}
.wrap{max-width:1120px;margin:0 auto;padding:44px 24px 72px}
.intro>*{animation:subir .6s steps(6) backwards}
.intro>*:nth-child(2){animation-delay:.1s}.intro>*:nth-child(3){animation-delay:.2s}
h1{font:700 3.4rem/1.05 var(--pix);margin:0 0 14px;text-shadow:4px 4px 0 var(--chip)}
h1 em{font-style:normal;color:var(--num)}
.sub{color:var(--mut);margin:0;font-size:1.05rem}
.barra{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:28px 0 12px}
.abas{display:inline-flex;max-width:100%;overflow-x:auto;scrollbar-width:none;background:var(--card);border:4px solid var(--borda);box-shadow:4px 4px 0 var(--borda)}
.aba{border:0;border-right:4px solid var(--borda);background:transparent;color:var(--mut);font:400 .62rem var(--tit);text-transform:uppercase;padding:13px 15px;cursor:pointer;white-space:nowrap}
.aba:last-child{border-right:0}
.aba:hover{color:var(--ink);background:var(--chip)}
.aba.on{background:var(--acc);color:var(--on-acc)}
.aba:focus-visible,.seletor select:focus-visible,a:focus-visible,.mais:focus-visible,.tema:focus-visible{outline:4px solid var(--acc2);outline-offset:3px}
.seletor select{appearance:none;-webkit-appearance:none;font:inherit;font-size:1rem;color:var(--ink);cursor:pointer;border:4px solid var(--borda);padding:8px 44px 8px 14px;box-shadow:4px 4px 0 var(--borda);background:var(--card) url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='6' shape-rendering='crispEdges'><path fill='%23889' d='M0 0h12v2H0zM2 2h8v2H2zM4 4h4v2H4z'/></svg>") no-repeat right 14px center}
.so-leitor{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.contagem{color:var(--mut);font-size:1rem;margin:0 0 24px;min-height:1.4em}
.thumb{display:block;position:relative;aspect-ratio:16/9;overflow:hidden;background-color:hsl(var(--h) 45% 30%);background-image:linear-gradient(45deg,rgba(255,255,255,.1) 25%,transparent 25%,transparent 75%,rgba(255,255,255,.1) 75%),linear-gradient(45deg,rgba(255,255,255,.1) 25%,transparent 25%,transparent 75%,rgba(255,255,255,.1) 75%);background-size:16px 16px;background-position:0 0,8px 8px}
.thumb span{position:absolute;left:14px;bottom:12px;font:400 .7rem var(--tit);color:#fff;text-shadow:2px 2px 0 #000}
.thumb img,.thumb canvas{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;image-rendering:pixelated;filter:contrast(1.15) saturate(1.25)}
.pill{position:absolute;top:12px;left:12px;z-index:2;pointer-events:none;background:var(--acc2);color:#1A1C2C;border:3px solid #1A1C2C;font:400 .55rem var(--tit);text-transform:uppercase;padding:6px 8px}
.meta{display:flex;gap:12px;font-size:.92rem;color:var(--mut);margin-bottom:6px}
.fonte{color:var(--acc);font-weight:700}
h2,h3{font-family:var(--pix);font-weight:700;margin:0}
h2{font-size:2.2rem;line-height:1.1}
h3{font-size:1.32rem;line-height:1.15}
h2 a::after,h3 a::after{content:"";position:absolute;inset:0;z-index:1}
.corpo p{margin:10px 0 0;color:var(--mut);font-size:1rem}
.destaque{display:grid;grid-template-columns:1.8fr 1fr;gap:32px;margin-bottom:60px}
.destaque[hidden],.card[hidden],.mais[hidden]{display:none}
.hero{position:relative;isolation:isolate;display:flex;align-items:flex-end;min-height:460px;border:4px solid var(--borda);box-shadow:var(--sombra);overflow:hidden;transition:transform .15s steps(3),box-shadow .15s steps(3);animation:subir .7s steps(7) .15s backwards}
.hero:hover{transform:translate(-4px,-4px);box-shadow:var(--sombra-h)}
.hero .fundo{position:absolute;inset:0;aspect-ratio:auto;z-index:-2}
.hero .fundo span{display:none}
.hero::after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(to top,rgba(5,6,12,.92) 0 34%,rgba(5,6,12,.62) 34% 56%,rgba(5,6,12,.3) 56% 74%,transparent 74%)}
.hero .texto{padding:28px;max-width:680px;color:#fff}
.hero .meta{align-items:center;color:#F4F4F4}
.hero h2{text-shadow:3px 3px 0 #000}
.hero .pill{position:static}
.hero .texto p{margin:12px 0 0;color:#F4F4F4}
.laterais{border-top:4px solid var(--borda)}
.lat{position:relative;display:flex;gap:16px;padding:20px 0;border-bottom:4px dashed var(--chip);transition:transform .15s steps(3);animation:subir .6s steps(6) backwards}
.lat:nth-child(1){animation-delay:.3s}.lat:nth-child(2){animation-delay:.42s}.lat:nth-child(3){animation-delay:.54s}
.lat:hover{transform:translateX(10px)}
.lat:hover h3,.card:hover h3{color:var(--acc)}
.num{font:400 1rem var(--tit);color:var(--num);min-width:2.6rem;padding-top:4px}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(262px,1fr));gap:30px}
.card{position:relative;background:var(--card);border:4px solid var(--borda);box-shadow:var(--sombra);display:flex;flex-direction:column;transition:transform .15s steps(3),box-shadow .15s steps(3)}
.card:hover{transform:translate(-4px,-4px);box-shadow:var(--sombra-h)}
.card .thumb{border-bottom:4px solid var(--borda)}
.card .corpo{padding:16px 18px 22px}
.js .card:not(.in){opacity:0}
.card.in{animation:subir .5s steps(6) backwards;animation-delay:calc(var(--i,0)*70ms)}
.mais{display:block;margin:52px auto 0;border:4px solid var(--borda);background:var(--acc2);color:#1A1C2C;font:400 .75rem var(--tit);text-transform:uppercase;padding:18px 26px;cursor:pointer;box-shadow:var(--sombra);transition:transform .12s steps(2),box-shadow .12s steps(2)}
.mais:hover{transform:translate(-3px,-3px);box-shadow:var(--sombra-h)}
.mais:active{transform:translate(5px,5px);box-shadow:0 0 0 var(--borda)}
.vazio{color:var(--mut)}
footer{margin-top:60px;padding-top:18px;border-top:4px dashed var(--chip);color:var(--mut);font-size:1rem}
@media (max-width:820px){.destaque{grid-template-columns:1fr;gap:26px}h1{font-size:2.3rem}h2{font-size:1.55rem}.hero{min-height:380px}.hero .texto{padding:20px}
.wrap{padding:30px 18px 56px}.topo-in{padding:12px 18px}.barra{flex-direction:column;align-items:stretch}.seletor select{width:100%}.logo{font-size:.8rem}}
@media (prefers-reduced-motion:reduce){*,*::before{animation:none!important;transition:none!important}.js .card:not(.in){opacity:1}}
</style>
</head>
<body>
<div class="progresso" id="progresso"></div>
<header class="topo"><div class="topo-in">
<a class="logo" href="#"><span class="ponto"></span>Radar Tech</a>
<button class="tema" id="tema" type="button" aria-label="Alternar entre tema claro e escuro" title="Alternar tema">
<svg class="i-sol" viewBox="0 0 8 8" width="24" height="24" fill="currentColor"><path d="M2 2h4v4H2zM3 0h2v1H3zM3 7h2v1H3zM0 3h1v2H0zM7 3h1v2H7zM1 1h1v1H1zM6 1h1v1H6zM1 6h1v1H1zM6 6h1v1H6z"/></svg>
<svg class="i-lua" viewBox="0 0 8 8" width="24" height="24" fill="currentColor"><path d="M2 0h3v1H2zM1 1h2v1H1zM0 2h2v3H0zM1 5h2v1H1zM6 5h2v1H6zM2 6h5v1H2z"/></svg>
</button>
</div></header>
<div class="wrap">
<section class="intro">
<h1>O dia em <em>tecnologia</em></h1>
<p class="sub">__TOTAL__ notícias das últimas 72 horas. Atualizado em __ATUALIZADO__.</p>
<div class="barra"><div class="abas" role="tablist" aria-label="Categorias">__CHIPS__</div><label class="seletor"><span class="so-leitor">Fonte</span><select id="fonte" aria-label="Filtrar por fonte"></select></label></div>
<p class="contagem" id="contagem"></p>
</section>
<main>
<section class="destaque">
<div>__HERO__</div>
<div class="laterais">__LATERAIS__</div>
</section>
<section class="grade">
__GRADE__
</section>
<button class="mais" id="mais" type="button">Ver mais notícias</button>
</main>
<footer>Os títulos levam ao site original de cada fonte.</footer>
</div>
<script>
(function(){
  var PAGINA=9, cat="", fonte="", n=PAGINA;
  function pixelar(img){
    var w=img.naturalWidth,h=img.naturalHeight;
    if(!w||!h)return;
    var cw=img.closest(".hero")?110:60,ch=Math.max(1,Math.round(cw*h/w));
    var c=document.createElement("canvas");c.width=cw;c.height=ch;
    var x=c.getContext("2d");x.imageSmoothingQuality="high";x.drawImage(img,0,0,cw,ch);
    img.replaceWith(c);
  }
  document.querySelectorAll(".thumb img").forEach(function(img){
    if(img.complete&&img.naturalWidth)pixelar(img);
    else img.addEventListener("load",function(){pixelar(img);});
  });
  var cards=[].slice.call(document.querySelectorAll(".grade .card"));
  var abas=[].slice.call(document.querySelectorAll(".aba"));
  var destaque=document.querySelector(".destaque");
  var mais=document.getElementById("mais");
  var sel=document.getElementById("fonte");
  var contagem=document.getElementById("contagem");
  function zerar(){cards.forEach(function(c){c.hidden=true;c.classList.remove("in");});}
  function bate(c){
    if(cat!==""&&("|"+c.dataset.cats+"|").indexOf("|"+cat+"|")<0)return false;
    if(fonte!==""&&c.dataset.fonte!==fonte)return false;
    return true;
  }
  function render(){
    var filtrando=cat!==""||fonte!=="";
    var vis=cards.filter(function(c){return filtrando?bate(c):(c.dataset.dest!=="1"&&c.dataset.so!=="1");});
    cards.forEach(function(c){
      var p=vis.indexOf(c);
      if(p<0||p>=n){c.hidden=true;c.classList.remove("in");}
    });
    var k=0;
    vis.slice(0,n).forEach(function(c){
      if(c.hidden||!c.classList.contains("in")){
        c.hidden=false;c.style.setProperty("--i",k++);
        void c.offsetWidth;c.classList.add("in");
      }
    });
    if(destaque)destaque.hidden=filtrando;
    contagem.textContent=filtrando?vis.length+(vis.length===1?" notícia":" notícias"):"";
    mais.hidden=vis.length<=n;
    mais.textContent="Ver mais notícias ("+(vis.length-n)+")";
  }
  function montarSelect(lista){
    sel.innerHTML="";
    var o=document.createElement("option");o.value="";o.textContent="Todas as fontes";sel.appendChild(o);
    lista.forEach(function(f){var x=document.createElement("option");x.value=f;x.textContent=f;sel.appendChild(x);});
    sel.value="";
  }
  abas.forEach(function(b){
    b.addEventListener("click",function(){
      abas.forEach(function(a){a.classList.remove("on");a.setAttribute("aria-selected","false");});
      b.classList.add("on");b.setAttribute("aria-selected","true");
      cat=b.dataset.cat;fonte="";n=PAGINA;
      montarSelect(b.dataset.fontes?b.dataset.fontes.split("|"):[]);
      zerar();render();
    });
  });
  sel.addEventListener("change",function(){fonte=sel.value;n=PAGINA;zerar();render();});
  mais.addEventListener("click",function(){n+=PAGINA;render();});
  document.getElementById("tema").addEventListener("click",function(){
    var d=document.documentElement,novo=d.dataset.theme==="dark"?"light":"dark";
    d.dataset.theme=novo;
    try{localStorage.setItem("tema",novo)}catch(e){}
  });
  var barra=document.getElementById("progresso");
  window.addEventListener("scroll",function(){
    var h=document.documentElement,max=h.scrollHeight-h.clientHeight;
    barra.style.transform="scaleX("+(max>0?h.scrollTop/max:0)+")";
  },{passive:true});
  montarSelect(abas[0].dataset.fontes.split("|"));
  zerar();render();
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
