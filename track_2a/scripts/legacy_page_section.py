"""Legacy selector (repository HEAD before the running-header selector), kept only for the audit comparison."""
import re,unicodedata

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

