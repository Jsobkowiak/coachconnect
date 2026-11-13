from pathlib import Path
import hashlib,json
out=Path('apps/exercise-catalog/src/exercise_catalog/data/diagrams');out.mkdir(exist_ok=True)
def line(x1,y1,x2,y2,cls='body'):
 return f'<path class="{cls}" d="M{x1} {y1}L{x2} {y2}"/>'
def person(head,neck,hip,arms,legs):
 x,y=head
 return f'<circle class="head" cx="{x}" cy="{y}" r="15"/>'+line(*neck,*hip)+''.join(line(*a,*b) for a,b in arms+legs)
def panel(x,title,art):return f'<g transform="translate({x} 0)"><text class="label" x="120" y="55" text-anchor="middle">{title}</text><path class="ground" d="M20 310H220"/>'+art+'</g>'
def doc(title,panels,note):
 return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="410" viewBox="0 0 1000 410" role="img" aria-label="{title}"><style>.body{{fill:none;stroke:#205449;stroke-width:8;stroke-linecap:round;stroke-linejoin:round}}.head{{fill:#f8e7c8;stroke:#205449;stroke-width:3}}.ground{{stroke:#c9d7ce;stroke-width:2}}.prop{{fill:none;stroke:#60766d;stroke-width:6;stroke-linejoin:round}}.ball{{fill:#e8b758;stroke:#8e6c20;stroke-width:2}}.arrow{{fill:none;stroke:#be8240;stroke-width:3;stroke-dasharray:7 5}}.label{{font:600 15px sans-serif;fill:#205449}}.note{{font:14px sans-serif;fill:#51645b}}</style><rect width="1000" height="410" fill="#f8faf6"/><text x="25" y="27" class="label">{title}</text>{panels}<text x="500" y="365" text-anchor="middle" class="note">{note}</text><text x="500" y="392" text-anchor="middle" class="note">Schéma simplifié du geste · CoachConnect · CC BY 4.0</text></svg>'''
stand=person((120,110),(120,130),(120,225),[((120,150),(95,200)),((120,150),(145,200))],[((120,225),(100,305)),((120,225),(140,305))])
crouch=person((145,180),(135,198),(95,240),[((135,200),(175,300)),((135,200),(157,300))],[((95,240),(145,275)),((145,275),(130,305)),((95,240),(70,275)),((70,275),(55,305))])
prone=person((185,266),(170,279),(80,286),[((160,280),(145,294)),((145,294),(170,304))],[((80,286),(25,300))])
jump=person((120,90),(120,110),(120,210),[((120,130),(80,65)),((120,130),(160,65))],[((120,210),(100,280)),((120,210),(140,280))])
burpee=doc('Burpee : passage au sol puis saut',panel(0,'1. Debout',stand)+panel(250,'2. Mains au sol',crouch)+panel(500,'3. Corps au sol',prone)+panel(750,'4. Retour et saut',jump),'Ramener les pieds près des mains avant de se redresser et sauter ; réception souple.')
wall=lambda: '<path class="prop" d="M207 100V310"/><circle class="prop" cx="207" cy="140" r="13"/>'
squat=person((115,160),(115,180),(92,245),[((115,195),(160,180)),((115,195),(155,210))],[((92,245),(145,255)),((145,255),(130,305)),((92,245),(70,280)),((70,280),(55,305))])+'<circle class="ball" cx="166" cy="195" r="18"/>'
throw=person((115,108),(115,128),(115,225),[((115,150),(170,115)),((115,150),(162,118))],[((115,225),(95,305)),((115,225),(135,305))])+ '<path class="arrow" d="M170 105Q195 75 206 115"/><circle class="ball" cx="185" cy="95" r="18"/>'
catch=person((120,110),(120,130),(120,225),[((120,150),(137,175)),((137,175),(155,174)),((120,150),(140,190)),((140,190),(155,185))],[((120,225),(100,305)),((120,225),(140,305))])+'<circle class="ball" cx="153" cy="174" r="18"/><path class="arrow" d="M195 150L163 170"/>'
wallball=doc('Wall ball : squat et lancer vers une cible',panel(50,'1. Squat, ballon proche',squat+wall())+panel(370,'2. Poussée et lancer',throw+wall())+panel(690,'3. Réception contrôlée',catch+wall()),'Recevoir devant la poitrine, puis absorber le retour du ballon avec les jambes.')
hang=person((125,140),(125,160),(125,235),[((125,180),(90,80)),((125,180),(160,80))],[((125,235),(110,305)),((125,235),(140,305))])+'<path class="prop" d="M50 80H200"/>'
raiselegs=person((125,140),(125,160),(100,235),[((125,180),(90,80)),((125,180),(160,80))],[((100,235),(195,175)),((195,175),(168,80)),((100,235),(185,170)),((185,170),(158,80))])+'<path class="prop" d="M50 80H205"/><path class="arrow" d="M195 290Q238 220 188 110"/>'
ttb=doc('Pieds à la barre : variante stricte, sans élan',panel(120,'1. Suspension stable',hang)+panel(560,'2. Pieds en contact',raiselegs),'Enrouler le bassin, toucher la barre avec les pieds, puis redescendre sous contrôle.')
ttb=ttb.replace('<path class="ground" d="M20 310H220"/>','')
rope='<path class="arrow" d="M88 205C0 65 235 65 153 205C208 360 24 360 88 205"/>'
jump_rope=person((120,95),(120,115),(120,210),[((120,135),(90,180)),((90,180),(85,205)),((120,135),(150,180)),((150,180),(155,205))],[((120,210),(102,275)),((120,210),(138,275))])+rope+'<text class="label" x="120" y="335" text-anchor="middle">2 passages sous les pieds</text>'
rope_start=person((120,110),(120,130),(120,225),[((120,150),(90,190)),((90,190),(85,205)),((120,150),(150,190)),((150,190),(155,205))],[((120,225),(100,305)),((120,225),(140,305))])+rope
du=doc('Double under : deux tours de corde pour un saut',panel(120,'1. Poignées près des hanches',rope_start)+panel(560,'2. Saut vertical et deux tours',jump_rope),'Faire tourner la corde avec les poignets ; conserver des sauts et des réceptions réguliers.')
seed_path=Path('apps/exercise-catalog/src/exercise_catalog/data/catalogue-fr.json');seed=json.loads(seed_path.read_text())
for key,content in [('burpee',burpee),('wall-ball',wallball),('toes-to-bar-stricts',ttb),('double-under',du)]:
 filename=hashlib.sha256(content.encode()).hexdigest()+'.svg';(out/filename).write_text(content)
 entry=next(r for r in seed['entries'] if r['key']==key);entry['diagram']=filename;entry['media_note']='Schéma original simplifié des étapes, rédigé pour cette fiche ; les positions et le matériel ont été comparés aux consignes.'
seed_path.write_text(json.dumps(seed,ensure_ascii=False,indent=2)+'\n')
print('4 schémas originaux ajoutés')
