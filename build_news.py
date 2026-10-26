"""Gera o index.html do Radar Tech com as notícias de tecnologia mais recentes (via RSS).

Para trocar as fontes, edite o dicionário FEEDS logo abaixo.
"""
import html
import re
import socket
from datetime import datetime, timedelta, timezone
from time import mktime
from zoneinfo import ZoneInfo

import feedparser

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
    "DeepMind": "https://blog.google/technology/google-deepmind/rss/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Hacker News": "https://hnrss.org/frontpage",
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
            itens.append({
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

    def card(i, destaque):
        resumo = f'<p>{esc(i["resumo"])}</p>' if i["resumo"] else ""
        pill = f'<span class="pill">{esc(i["fonte"])}</span>' if i["imagem"] else ""
        oculto = " hidden" if destaque else ""
        return (f'<article class="card" data-fonte="{esc(i["fonte"])}" '
                f'data-dest="{1 if destaque else 0}"{oculto}>{pill}{thumb(i)}'
                f'<div class="corpo">{meta(i, False)}{titulo(i)}{resumo}</div></article>')

    fontes = sorted({i["fonte"] for i in itens})
    chips = '<button class="chip on" data-fonte="">Todas</button>' + "".join(
        f'<button class="chip" data-fonte="{esc(f)}">{esc(f)}</button>' for f in fontes)

    hero_html = laterais_html = grade_html = ""
    if itens:
        hero = next((i for i in itens if i["imagem"]), itens[0])
        laterais, vistas = [], {hero["fonte"]}
        for i in itens:
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
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Newsreader:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<style>
:root{--bg:#F4F6F9;--card:#fff;--ink:#121C26;--mut:#586775;--line:#DCE3E9;--acc:#0B6E8A;--acc2:#7A5AF8;--chip:#E5EBF0;
--glass:rgba(244,246,249,.78);--g1:rgba(11,110,138,.17);--g2:rgba(122,90,248,.12);--sombra:0 14px 34px rgba(18,28,38,.12);--r:18px;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0B141B;--card:#122029;--ink:#E8EEF2;--mut:#93A3B0;--line:#21323E;--acc:#5CC0DC;--acc2:#A78BFA;--chip:#182833;--glass:rgba(11,20,27,.78);--g1:rgba(92,192,220,.14);--g2:rgba(167,139,250,.13);--sombra:0 14px 34px rgba(0,0,0,.45)}}
:root[data-theme="dark"]{--bg:#0B141B;--card:#122029;--ink:#E8EEF2;--mut:#93A3B0;--line:#21323E;--acc:#5CC0DC;--acc2:#A78BFA;--chip:#182833;--glass:rgba(11,20,27,.78);--g1:rgba(92,192,220,.14);--g2:rgba(167,139,250,.13);--sombra:0 14px 34px rgba(0,0,0,.45)}
*{box-sizing:border-box}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "DM Sans",system-ui,sans-serif;transition:background-color .4s,color .4s}
body::before{content:"";position:fixed;inset:-25%;z-index:-1;pointer-events:none;
background:radial-gradient(38% 32% at 18% 14%,var(--g1),transparent 70%),radial-gradient(34% 30% at 86% 8%,var(--g2),transparent 70%);animation:flutuar 24s ease-in-out infinite alternate}
@keyframes flutuar{to{transform:translate3d(4%,6%,0) scale(1.08)}}
@keyframes subir{from{opacity:0;transform:translateY(22px)}}
@keyframes pulso{0%{box-shadow:0 0 0 0 var(--acc)}70%,100%{box-shadow:0 0 0 9px transparent}}
a{color:inherit;text-decoration:none}
.progresso{position:fixed;top:0;left:0;right:0;height:3px;z-index:100;transform:scaleX(0);transform-origin:left;background:linear-gradient(90deg,var(--acc),var(--acc2))}
.topo{position:sticky;top:env(safe-area-inset-top,0px);z-index:50;background:var(--glass);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.topo-in{max-width:1120px;margin:0 auto;padding:12px 24px;display:flex;align-items:center;justify-content:space-between}
.logo{display:flex;align-items:center;gap:10px;font:600 1.4rem "Newsreader",Georgia,serif;letter-spacing:-.01em}
.ponto{width:9px;height:9px;border-radius:50%;background:var(--acc);animation:pulso 2.2s infinite}
.tema{position:relative;width:42px;height:42px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;transition:transform .3s,border-color .3s}
.tema:hover{transform:rotate(18deg) scale(1.06);border-color:var(--acc)}
.tema svg{position:absolute;inset:0;margin:auto;transition:transform .5s cubic-bezier(.3,.9,.3,1),opacity .3s}
:root[data-theme="dark"] .i-lua,:root:not([data-theme="dark"]) .i-sol{opacity:0;transform:rotate(-90deg) scale(.4)}
.wrap{max-width:1120px;margin:0 auto;padding:44px 24px 72px}
.intro>*{animation:subir .8s cubic-bezier(.2,.7,.2,1) backwards}
.intro>*:nth-child(2){animation-delay:.1s}.intro>*:nth-child(3){animation-delay:.2s}
h1{font:500 3.6rem/1.02 "Newsreader",Georgia,serif;letter-spacing:-.025em;margin:0 0 12px}
h1 em{font-style:italic;background:linear-gradient(90deg,var(--acc),var(--acc2));-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--mut);margin:0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:26px 0 34px}
.chip{border:1px solid transparent;background:var(--chip);color:var(--ink);font:inherit;font-size:.9rem;padding:7px 16px;border-radius:999px;cursor:pointer;transition:background-color .25s,color .25s,transform .25s,border-color .25s}
.chip:hover{border-color:var(--acc);transform:translateY(-2px)}
.chip.on{background:var(--acc);color:#fff}
.chip:focus-visible,a:focus-visible,.mais:focus-visible,.tema:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
.thumb{display:block;position:relative;aspect-ratio:16/9;overflow:hidden;background:radial-gradient(circle at 82% 18%,rgba(255,255,255,.22),transparent 45%),linear-gradient(135deg,hsl(var(--h) 45% 36%),hsl(var(--h) 55% 20%))}
.thumb span{position:absolute;left:16px;bottom:12px;font:500 1.15rem "Newsreader",Georgia,serif;color:#fff;opacity:.85}
.thumb img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .8s cubic-bezier(.2,.7,.2,1)}
.pill{position:absolute;top:12px;left:12px;z-index:2;pointer-events:none;background:rgba(8,16,22,.6);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);color:#fff;font-size:.74rem;font-weight:600;letter-spacing:.02em;padding:4px 11px;border-radius:999px}
.meta{display:flex;gap:12px;font-size:.84rem;color:var(--mut);margin-bottom:6px}
.fonte{color:var(--acc);font-weight:600}
h2,h3{font-family:"Newsreader",Georgia,serif;font-weight:500;margin:0}
h2{font-size:2.3rem;line-height:1.12}
h3{font-size:1.28rem;line-height:1.27;transition:color .25s}
h2 a::after,h3 a::after{content:"";position:absolute;inset:0;z-index:1}
.corpo p{margin:10px 0 0;color:var(--mut);font-size:.96rem}
.destaque{display:grid;grid-template-columns:1.8fr 1fr;gap:28px;margin-bottom:56px}
.destaque[hidden],.card[hidden],.mais[hidden]{display:none}
.hero{position:relative;isolation:isolate;display:flex;align-items:flex-end;min-height:460px;border-radius:var(--r);overflow:hidden;box-shadow:var(--sombra);animation:subir .9s cubic-bezier(.2,.7,.2,1) .15s backwards}
.hero .fundo{position:absolute;inset:0;aspect-ratio:auto;z-index:-2}
.hero .fundo span{display:none}
.hero::after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(to top,rgba(5,12,18,.9),rgba(5,12,18,.4) 55%,transparent)}
.hero:hover .fundo img{transform:scale(1.06)}
.hero .texto{padding:30px;max-width:660px;color:#fff}
.hero .meta{align-items:center;color:rgba(255,255,255,.82)}
.hero .pill{position:static;background:rgba(255,255,255,.18)}
.hero .texto p{margin:12px 0 0;color:rgba(255,255,255,.84)}
.laterais{border-top:1px solid var(--line)}
.lat{position:relative;display:flex;gap:16px;padding:20px 0;border-bottom:1px solid var(--line);transition:transform .35s cubic-bezier(.2,.7,.2,1);animation:subir .8s cubic-bezier(.2,.7,.2,1) backwards}
.lat:nth-child(1){animation-delay:.3s}.lat:nth-child(2){animation-delay:.42s}.lat:nth-child(3){animation-delay:.54s}
.lat:hover{transform:translateX(8px)}
.lat:hover h3,.card:hover h3{color:var(--acc)}
.num{font:italic 500 2rem/1 "Newsreader",Georgia,serif;color:var(--acc);opacity:.55;min-width:2.2rem}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(262px,1fr));gap:22px}
.card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;display:flex;flex-direction:column;transition:transform .4s cubic-bezier(.2,.7,.2,1),box-shadow .4s,border-color .3s,background-color .4s}
.card:hover{transform:translateY(-6px);box-shadow:var(--sombra);border-color:var(--acc)}
.card:hover .thumb img{transform:scale(1.07)}
.card .corpo{padding:16px 18px 22px}
.js .card:not(.in){opacity:0}
.card.in{animation:subir .7s cubic-bezier(.2,.7,.2,1) backwards;animation-delay:calc(var(--i,0)*60ms)}
.mais{display:block;margin:40px auto 0;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit;font-weight:500;padding:13px 30px;border-radius:999px;cursor:pointer;transition:background-color .3s,color .3s,transform .3s,border-color .3s}
.mais:hover{background:var(--acc);border-color:var(--acc);color:#fff;transform:translateY(-3px)}
.vazio{color:var(--mut)}
footer{margin-top:56px;color:var(--mut);font-size:.85rem}
@media (max-width:820px){.destaque{grid-template-columns:1fr;gap:22px}h1{font-size:2.6rem}h2{font-size:1.65rem}.hero{min-height:380px}.hero .texto{padding:22px}
.wrap{padding:30px 18px 56px}.topo-in{padding:10px 18px}.chips{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none}.chip{flex:none}}
@media (prefers-reduced-motion:reduce){*,*::before{animation:none!important;transition:none!important}.js .card:not(.in){opacity:1}}
</style>
</head>
<body>
<div class="progresso" id="progresso"></div>
<header class="topo"><div class="topo-in">
<a class="logo" href="#"><span class="ponto"></span>Radar Tech</a>
<button class="tema" id="tema" type="button" aria-label="Alternar entre tema claro e escuro" title="Alternar tema">
<svg class="i-sol" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
<svg class="i-lua" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
</button>
</div></header>
<div class="wrap">
<section class="intro">
<h1>O dia em <em>tecnologia</em></h1>
<p class="sub">__TOTAL__ notícias das últimas 72 horas. Atualizado em __ATUALIZADO__.</p>
<div class="chips" role="group" aria-label="Filtrar por fonte">__CHIPS__</div>
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
  var PAGINA=12, filtro="", n=PAGINA;
  var cards=[].slice.call(document.querySelectorAll(".grade .card"));
  var destaque=document.querySelector(".destaque");
  var mais=document.getElementById("mais");
  function zerar(){cards.forEach(function(c){c.hidden=true;c.classList.remove("in");});}
  function render(){
    var vis=cards.filter(function(c){
      return filtro===""?c.dataset.dest!=="1":c.dataset.fonte===filtro;
    });
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
    if(destaque)destaque.hidden=filtro!=="";
    mais.hidden=vis.length<=n;
    mais.textContent="Ver mais notícias ("+(vis.length-n)+")";
  }
  document.querySelectorAll(".chip").forEach(function(b){
    b.addEventListener("click",function(){
      document.querySelectorAll(".chip").forEach(function(c){c.classList.remove("on");});
      b.classList.add("on");
      filtro=b.dataset.fonte;n=PAGINA;zerar();render();
    });
  });
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
