"""Local context candidates. Uses request + PDF only; never gold or prior outputs."""
import math,re,unicodedata
from collections import Counter

def normalize(text):
    text=re.sub(r'(\w)\s*[-\u00ad]\s*\n\s*(?=\w)',r'\1',text)
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c)).split())
STOP={'volksinitiative','initiative','iniziativa','populaire','popolare','federale','fur','eine','ein','der','die','das','des','du','de','la','le','les','une','un','per','una','un','di','della','del','federale'}
CONCEPTS={
'council':['bundesrat','bundesrates','conseil federal','consiglio federale'],
'parliament':['bundesversammlung','parlament','parliament','parlement','parlamento','assemblee federale'],
'committee':['komitee','comite','comitato'],
'pension':['rente','renten','pension','pensione','pensioni','retraite','ahv','avs'],
'approve':['annehmen','annahme','accepter','acceptation','accogliere','approvare'],
'reject':['ablehnen','ablehnung','rejeter','rejet','respingere'],
'finance':['finanzen','finanzi','finanzier','finances','financ','finanziar'],
'generation':['generation','generazione','generazioni'],
'condition':['wenn','falls','sofern','si','se'],
'negation':['nicht','kein','keine','pas','non','nein'],
}
def tokens(text):
    n=normalize(text);words=[w for w in re.findall(r'\w+',n) if len(w)>2 and w not in STOP]
    words.extend('concept_'+k for k,v in CONCEPTS.items() if any(s in n for s in v))
    return words

def page_section(pages,vote):
    query=set(tokens(vote))
    def match(text):return len(query & set(tokens(text)))/max(1,len(query))
    starts=[i for i,p in enumerate(pages) if i>=3 and re.search(r'\b(?:im detail|en detail|in dettaglio)\b',normalize(p[:500]))]
    if not starts:return list(range(len(pages))),{'fallback':'no section markers'}
    start=max(starts,key=lambda i:(match(pages[i][:900]),i))
    confidence=match(pages[start][:900])
    if confidence<0.45:return list(range(len(pages))),{'fallback':'weak vote match','confidence':confidence}
    end=next((i for i in starts if i>start),len(pages))
    # Trailing voting recommendations refer to every vote; retain as context.
    selected=set(range(start,end))
    summaries=list(range(3,min(starts)))
    if summaries:
        summary=max(summaries,key=lambda i:match(pages[i][:800]))
        if match(pages[summary][:800])>=0.45:selected.update(i for i in (summary,summary+1) if i<min(starts))
    if len(pages)-1>=end:selected.add(len(pages)-1)
    return sorted(selected),{'detail_start_page':start+1,'detail_end_page':end,'confidence':confidence,'selected_pages':[i+1 for i in sorted(selected)]}

def chunks(text,limit=1200):
    # Cut only at sentence/paragraph boundaries; preserve original bytes/spans.
    boundaries=[0]+[m.end() for m in re.finditer(r'\n\s*\n|(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ])',text)]+[len(text)]
    start=0;result=[]
    for end in boundaries[1:]:
        if end-start>=limit:
            result.append(text[start:end]);start=end
    if start<len(text):result.append(text[start:])
    return [x for x in result if x.strip()]

def selected_context(pages,case,variant):
    selected,meta=page_section(pages,case['vote'])
    if variant=='vote_pages':
        return '\n\n'.join(f'[PAGE {i+1}]\n{pages[i]}' for i in selected),meta
    entries=[(i,c) for i in selected for c in chunks(pages[i])]
    bag=[Counter(tokens(c)) for i,c in entries]
    query=set(tokens(case['claim']['text']))
    df=Counter(w for b in bag for w in b)
    avg=sum(sum(b.values()) for b in bag)/max(1,len(bag))
    def bm25(b):
        length=sum(b.values());return sum(math.log(1+(len(bag)-df[w]+0.5)/(df[w]+0.5)) * (b[w]*2.2)/(b[w]+1.2*(0.25+0.75*length/max(1,avg))) for w in query if b[w])
    top=sorted(range(len(entries)),key=lambda i:bm25(bag[i]),reverse=True)[:8]
    chosen=set(top)
    claim_numbers=set(re.findall(r'\b\d+(?:[.,]\d+)?\b',case['claim']['text']))
    for index,(page,text) in enumerate(entries):
        # Keep law text at the end of the chosen proposal and numeric matches.
        if page>=meta.get('detail_end_page',len(pages))-2 and page<meta.get('detail_end_page',len(pages)):
            chosen.add(index)
        if claim_numbers & set(re.findall(r'\b\d+(?:[.,]\d+)?\b',text)):chosen.add(index)
    for concept in ('concept_council','concept_parliament','concept_committee'):
        eligible=[i for i,b in enumerate(bag) if concept in b]
        if eligible:chosen.add(max(eligible,key=lambda i:bm25(bag[i])))
    # A context budget protects against a pathological number/actor expansion.
    ordered=sorted(chosen,key=lambda i:bm25(bag[i]),reverse=True)
    kept=[];used=0
    for index in ordered:
        length=len(entries[index][1])
        if used+length<=18000:kept.append(index);used+=length
    kept.sort()
    meta.update(chunks_kept=len(kept),chunks_total=len(entries),context_chars=used)
    return '\n\n'.join(f'[PAGE {entries[i][0]+1}]\n{entries[i][1]}' for i in kept),meta
