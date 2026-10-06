import os, json, hashlib, html, re, urllib.parse, urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

ROOT=os.path.dirname(os.path.dirname(__file__))
CFG=json.load(open(os.path.join(ROOT,'config','sources.json')))
FEED=os.path.join(ROOT,'data','feed.json')
try: old=json.load(open(FEED))
except Exception: old={'items':[]}
items={x['id']:x for x in old.get('items',[]) if x.get('id')}

def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s or ''))).strip()
def uid(*p): return hashlib.sha256('|'.join(str(x) for x in p).encode()).hexdigest()[:20]
def add(x): items[x['id']]=x

def rss(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 MeghalayaTracker/2.0'})
    with urllib.request.urlopen(req,timeout=25) as r: return ET.fromstring(r.read())

def google_news_query(query):
    url='https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-IN&gl=IN&ceid=IN:en'
    return rss(url)

def source_tier_name(tier):
    return {'meghalaya_media':'Meghalaya media','official_institutional':'Official / institutional','regional_national_media':'Regional / national media'}.get(tier,tier)

def curated_news(leader):
    # Search each approved domain explicitly. This prevents unrelated outlets from
    # entering the tracker simply because Google News happened to rank them.
    for tier, sources in CFG.get('source_tiers',{}).items():
        for src_cfg in sources:
            domain=src_cfg['domain']; approved_name=src_cfg['name']
            for base in leader['queries']:
                q=f'{base} site:{domain}'
                try: root=google_news_query(q)
                except Exception as e:
                    print('news',leader['id'],domain,e); continue
                for n in root.findall('.//item')[:12]:
                    title=clean(n.findtext('title')); link=n.findtext('link') or ''; desc=clean(n.findtext('description'))
                    if not title or not link: continue
                    pub=n.findtext('pubDate') or ''
                    try: dt=parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
                    except Exception: dt=datetime.now(timezone.utc).isoformat()
                    rss_source=n.find('source')
                    rss_source_name=(rss_source.text or '').strip() if rss_source is not None else ''
                    add({
                        'id':uid('news',leader['id'],title,link), 'leader':leader['id'], 'date':dt,
                        'type':'news', 'category':'News', 'title':title, 'summary':desc[:500],
                        'source':approved_name, 'reported_source':rss_source_name or approved_name,
                        'source_domain':domain, 'source_tier':source_tier_name(tier),
                        'url':link, 'primary': tier == 'official_institutional'
                    })

def youtube_channel_videos(leader):
    # Only configured/verified channels are queried. There is deliberately no
    # broad name search, so third-party videos cannot be mislabeled as official.
    key=os.getenv('YOUTUBE_API_KEY')
    if not key: return
    sources=[]
    for ch in leader.get('youtube_channel_ids',[]):
        sources.append({'channel_id':ch,'name':leader['name'],'kind':'Official leader channel','primary':True})
    for src in CFG.get('youtube_sources',{}).get('leaders',[]):
        if src.get('leader') == leader['id']: sources.append(src)
    for src in CFG.get('youtube_sources',{}).get('parties',[]):
        if src.get('leader') == leader['id']: sources.append(src)
    for src in CFG.get('youtube_sources',{}).get('institutional',[]):
        sources.append(src)

    seen=set()
    for src in sources:
        channel=src.get('channel_id')
        if not channel or channel in seen: continue
        seen.add(channel)
        params=urllib.parse.urlencode({'part':'snippet','channelId':channel,'q':leader['name'],'type':'video','order':'date','maxResults':10,'key':key})
        try:
            data=json.load(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/search?'+params,timeout=25))
            for r in data.get('items',[]):
                vid=r.get('id',{}).get('videoId'); sn=r.get('snippet',{})
                if not vid: continue
                add({
                    'id':uid('yt',vid,leader['id']), 'leader':leader['id'], 'date':sn.get('publishedAt'),
                    'type':'youtube', 'category':'Video', 'title':clean(sn.get('title')),
                    'summary':clean(sn.get('description'))[:500], 'source':src.get('name') or sn.get('channelTitle','YouTube'),
                    'source_tier':src.get('kind','Verified YouTube source'), 'url':'https://www.youtube.com/watch?v='+vid,
                    'video_id':vid, 'primary':bool(src.get('primary',False))
                })
        except Exception as e: print('youtube',leader['id'],channel,e)

def x_api(leader):
    token=os.getenv('X_BEARER_TOKEN'); handles=leader.get('x_handles',[])
    if not token or not handles: return
    for handle in handles:
        q=f'from:{handle} -is:retweet'
        url='https://api.x.com/2/tweets/search/recent?'+urllib.parse.urlencode({'query':q,'max_results':10,'tweet.fields':'created_at'})
        req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token})
        try:
            data=json.load(urllib.request.urlopen(req,timeout=25))
            for t in data.get('data',[]):
                text=clean(t.get('text')); tid=t['id']
                add({'id':uid('x',tid),'leader':leader['id'],'date':t.get('created_at'),'type':'x','category':'Official social','title':text[:140], 'summary':text,'source':'X @'+handle,'source_tier':'Official leader social','url':f'https://x.com/{handle}/status/{tid}','primary':True})
        except Exception as e: print('x',handle,e)

def meta_api(leader):
    token=os.getenv('META_ACCESS_TOKEN')
    if not token: return
    for page in leader.get('facebook_page_ids',[]):
        url=f'https://graph.facebook.com/v24.0/{page}/posts?'+urllib.parse.urlencode({'fields':'id,message,created_time,permalink_url','limit':10,'access_token':token})
        try:
            data=json.load(urllib.request.urlopen(url,timeout=25))
            for p in data.get('data',[]):
                msg=clean(p.get('message')); pid=p['id']
                add({'id':uid('fb',pid),'leader':leader['id'],'date':p.get('created_time'),'type':'facebook','category':'Official social','title':msg[:140] or 'Facebook post','summary':msg,'source':'Official Facebook','source_tier':'Official leader social','url':p.get('permalink_url','https://facebook.com'),'primary':True})
        except Exception as e: print('facebook',page,e)
    for ig in leader.get('instagram_user_ids',[]):
        url=f'https://graph.facebook.com/v24.0/{ig}/media?'+urllib.parse.urlencode({'fields':'id,caption,timestamp,permalink,media_type','limit':10,'access_token':token})
        try:
            data=json.load(urllib.request.urlopen(url,timeout=25))
            for p in data.get('data',[]):
                cap=clean(p.get('caption')); pid=p['id']
                add({'id':uid('ig',pid),'leader':leader['id'],'date':p.get('timestamp'),'type':'instagram','category':'Official social','title':cap[:140] or 'Instagram post','summary':cap,'source':'Official Instagram','source_tier':'Official leader social','url':p.get('permalink','https://instagram.com'),'primary':True})
        except Exception as e: print('instagram',ig,e)

for leader in CFG['leaders']:
    curated_news(leader)
    youtube_channel_videos(leader)
    x_api(leader)
    meta_api(leader)

out=list(items.values())
out.sort(key=lambda x:x.get('date') or '',reverse=True)
out=out[:500]
json.dump({'generated_at':datetime.now(timezone.utc).isoformat(),'status':'updated','items':out},open(FEED,'w'),indent=2,ensure_ascii=False)
print('wrote',len(out),'items')
