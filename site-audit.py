"""Reusable SEO and anti-'vibe-coded' audit for a static site folder.
Usage: python3 site-audit.py /path/to/site  (serves nothing, reads files only)"""
import os,re,json,glob,colorsys,subprocess,sys
from html.parser import HTMLParser
D=sys.argv[1] if len(sys.argv)>1 else '/mnt/user-data/outputs/deploy'
pages=['portfolio.html']+sorted(os.path.relpath(p,D) for p in glob.glob(D+'/projects/*.html'))+['privacy.html','terms.html','404.html']
INDEXABLE=[p for p in pages if p not in('privacy.html','terms.html','404.html')]
res=[]
def chk(n,ok,d=''):res.append((n,ok,d))
class P(HTMLParser):
    def __init__(s):
        super().__init__();s.title='';s.t=False;s.meta={};s.links=[];s.h=[];s.cur=None;s.imgs=[];s.btn=[];s.canon=None;s.ld=[];s.l=False;s.ids=set();s.text=[];s.skip=0
    def handle_starttag(s,t,a):
        a=dict(a)
        if 'id' in a:s.ids.add(a['id'])
        if t=='title':s.t=True
        if t=='meta' and (a.get('name') or a.get('property')):s.meta[a.get('name') or a.get('property')]=a.get('content','')
        if t=='link' and a.get('rel')=='canonical':s.canon=a.get('href')
        if t=='a' and 'href' in a:s.links.append(a['href'])
        if t in('h1','h2','h3','h4'):s.cur=t;s.h.append([t,''])
        if t=='img':s.imgs.append(a)
        if t=='button':s.btn.append(a)
        if t in('script','style'):
            s.skip+=1
            if a.get('type')=='application/ld+json':s.l=True;s.ld.append('')
    def handle_endtag(s,t):
        if t=='title':s.t=False
        if t in('h1','h2','h3','h4'):s.cur=None
        if t in('script','style'):s.skip-=1;s.l=False
    def handle_data(s,d):
        if s.t:s.title+=d
        if s.l:s.ld[-1]+=d
        if s.cur and s.h:s.h[-1][1]+=d
        if not s.skip:s.text.append(d)
data={}
for p in pages:
    src=open(f'{D}/{p}',encoding='utf8').read();x=P();x.feed(src);data[p]=(x,src)
allsrc=''.join(v[1] for v in data.values())
for p in INDEXABLE+['privacy.html','terms.html']:
    w=len(' '.join(data[p][0].text).split());chk(f'[{p}] content is in plain HTML without JavaScript',w>150,f'{w} words')
t=[data[p][0].title.strip() for p in pages];chk('Titles unique',len(set(t))==len(t));chk('Titles under 60 characters',all(len(x)<60 for x in t),str([len(x) for x in t]))
ds=[data[p][0].meta.get('description','') for p in pages];chk('Meta descriptions present and unique',all(ds) and len(set(ds))==len(ds));chk('Meta descriptions 50 to 160 characters',all(50<=len(x)<=160 for x in ds))
sm=open(D+'/sitemap.xml').read() if os.path.exists(D+'/sitemap.xml') else '';rb=open(D+'/robots.txt').read() if os.path.exists(D+'/robots.txt') else ''
chk('sitemap.xml lists every indexable page',all((('/' if p=='portfolio.html' else '/'+p) in sm) for p in INDEXABLE),f'{sm.count("<loc>")} URLs')
chk('robots.txt exists with a Sitemap line',bool(rb) and 'Sitemap:' in rb);chk('AI crawlers not blocked',not re.search(r'(?im)^User-agent:\s*(GPTBot|ClaudeBot|PerplexityBot|CCBot|Google-Extended)\s*\n\s*Disallow:\s*/\s*$',rb))
bad=[(p,l) for p in pages for l in data[p][0].links if (l.startswith('#') and len(l)>1 and (l[1:] not in data[p][0].ids or l.startswith(('#/','#!'))))]
chk('No hash-routing URLs; every #anchor has a target',not bad,str(bad[:4]))
chk('No buttons used for navigation',not [p for p in pages for b in data[p][0].btn if 'location' in b.get('onclick','')])
for p in pages:
    x=data[p][0];h1=[h for h in x.h if h[0]=='h1'];chk(f'[{p}] exactly one H1',len(h1)==1,h1[0][1].strip()[:40] if h1 else '')
    lv=[int(h[0][1]) for h in x.h];chk(f'[{p}] heading levels do not skip',not any(b-a>1 for a,b in zip(lv,lv[1:])))
chk('H1s unique (no cannibalization)',len({[h for h in data[p][0].h if h[0]=='h1'][0][1].strip() for p in pages})==len(pages))
chk('Every image has alt text',not [i for p in pages for i in data[p][0].imgs if not i.get('alt')]);chk('Every image has width and height',not [i for p in pages for i in data[p][0].imgs if not(i.get('width') and i.get('height'))])
imgs=glob.glob(D+'/images/*')+glob.glob(D+'/*.png');big=[(os.path.basename(f),os.path.getsize(f)//1024) for f in imgs if os.path.getsize(f)>200*1024]
chk('No image over 200 KB',not big,str(big) if big else 'largest '+str(max((os.path.getsize(f)//1024,os.path.basename(f)) for f in imgs)))
chk('No uncompressed png/jpg left in /images',not [f for f in os.listdir(D+'/images') if f.endswith(('.png','.jpg','.jpeg'))])
chk('No lorem ipsum or placeholder text',not re.search(r'lorem ipsum|TODO|FIXME|coming soon',allsrc,re.I))
missing=[]
for p in pages:
    for m in re.findall(r'(?:src|href)="([^"#?]+)"',data[p][1]):
        if m.startswith(('http','mailto:','tel:','data:')):continue
        path=m.lstrip('/') if m.startswith('/') else os.path.normpath(os.path.join(os.path.dirname(p),m))
        if path in('','.'):continue
        if not os.path.exists(os.path.join(D,path)):missing.append((p,m))
chk('No broken internal links or missing files',not missing,str(missing[:5]));chk('Custom 404 page exists',os.path.exists(D+'/404.html'))
gh=sorted({l for p in pages for l in data[p][0].links if 'github.com/' in l});bg=[]
for l in gh:
    m=re.match(r'https://github.com/([^/]+)/([^/#?]+)',l)
    if m:
        r=subprocess.run(['git','ls-remote','--exit-code',f'https://github.com/{m.group(1)}/{m.group(2)}.git','HEAD'],capture_output=True,text=True,timeout=40)
        if r.returncode:bg.append(l)
chk('GitHub links resolve',not bg,f'{len(gh)} checked')
for p in pages:chk(f'[{p}] canonical tag',bool(data[p][0].canon and data[p][0].canon.startswith('https://')))
for p in INDEXABLE:
    try:
        j=[json.loads(x) for x in data[p][0].ld];chk(f'[{p}] valid JSON-LD schema',bool(j),', '.join(str(n.get('@type')) for g in j for n in g.get('@graph',[g])))
    except Exception as e:chk(f'[{p}] valid JSON-LD schema',False,str(e))
inb={p:0 for p in pages}
for p in pages:
    for l in data[p][0].links:
        if l.startswith(('http','mailto:','#')):continue
        l=l.split('#')[0].split('?')[0];t='portfolio.html' if l in('','/') else (l.lstrip('/') if l.startswith('/') else os.path.normpath(os.path.join(os.path.dirname(p),l)))
        if t in inb and t!=p:inb[t]+=1
chk('No orphan pages',not [p for p,c in inb.items() if c==0 and p not in('404.html','portfolio.html')],str(inb))
chk('Real pages indexable; legal and 404 noindex',all('noindex' not in data[p][0].meta.get('robots','') for p in INDEXABLE) and all('noindex' in data[p][0].meta.get('robots','') for p in('privacy.html','terms.html','404.html')))
chk('Viewport, Open Graph and Twitter tags on every page',all(k in data[p][0].meta for p in pages for k in('viewport','og:title','og:description','og:image','twitter:card')))
chk('No third-party scripts, fonts or trackers',not [m for m in re.findall(r'(?:src|href)="(https?://[^"]+)"',allsrc) if m.endswith(('.js','.css')) or 'fonts.g' in m or 'cdn' in m or 'analytics' in m])
css=' '.join(re.findall(r'<style>([\s\S]*?)</style>',allsrc))
def purple():
    o=[]
    for h in set(re.findall(r'#([0-9a-fA-F]{6})\b',css)):
        r,g,b=[int(h[i:i+2],16)/255 for i in(0,2,4)];H,S,V=colorsys.rgb_to_hsv(r,g,b)
        if S>.2 and 255<=H*360<=320:o.append('#'+h)
    return o
chk('No purple colors or gradients',not purple(),str(purple()));chk('No glass or blur effects',not re.search(r'backdrop-filter|filter:\s*blur',css));chk('No glowing orbs or radial gradients',not re.search(r'radial-gradient',css))
chk('No dot-grid or pattern backgrounds',not re.search(r'background-image:\s*(url|radial)',css));chk('No Inter font',not re.search(r'font-family:[^;}]*\bInter\b',css))
chk('No emojis',not re.search(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728]',allsrc));chk('No em dashes',allsrc.count('\u2014')==0 and '&mdash;' not in allsrc)
chk('No sparkle or Lucide icons',not re.search(r'sparkle|lucide|feather',allsrc,re.I));chk('No fake testimonials, reviews or pricing tiers',not re.search(r'testimonial|happy customers|per month|pricing|most popular',allsrc,re.I))
chk('No three-cards-in-a-row or bento grids',not re.search(r'grid-template-columns:\s*(repeat\(3|1fr 1fr 1fr)',css))
chk('No hover animations',not re.search(r':hover\{[^}]*(transform|animation|transition)',css))
chk('Custom favicon (not default Vite or React)',all(os.path.exists(f'{D}/{f}') for f in['favicon.svg','favicon.ico','favicon-32.png','apple-touch-icon.png']))
f=sum(1 for r in res if not r[1])
for n,ok,d in res:print(('PASS ' if ok else 'FAIL ')+n+(f'  ({d})' if d else ''))
print(f'\n{len(res)-f} passed, {f} failed')