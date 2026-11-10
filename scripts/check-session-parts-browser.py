"""PC composition/cross-block copy, then mobile recording on an isolated account."""
import os, json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from training_test_auth import authenticated_context
BASE=os.environ.get('TRAINING_URL','http://localhost:18081')
assert ':18081' in BASE
OUT=Path('.local/session-parts-qa'); OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=authenticated_context(browser,BASE,profile=True,viewport={'width':1440,'height':1000})
    page=context.new_page(); errors=[]; page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(BASE+'/#blocs')
    page.get_by_role('button',name='+ Créer un bloc',exact=True).click()
    page.get_by_label('Nom du bloc',exact=True).fill('Force et deux AMRAP')
    page.get_by_label('Durée (semaines)',exact=True).fill('1')
    page.get_by_role('button',name='+ Séance',exact=True).click()
    page.get_by_label('Nom de la séance',exact=True).fill('WOD composé')
    def exercise(query):
        page.get_by_role('button',name='+ Ajouter un exercice',exact=True).click()
        page.get_by_label('Rechercher un exercice',exact=True).fill(query)
        page.get_by_role('button',name='Ajouter à la séance',exact=True).first.click()
    exercise('squat')
    page.get_by_role('button',name='+ Ajouter une partie',exact=True).click()
    page.get_by_label('Nom de la partie',exact=True).fill('AMRAP A')
    exercise('traction')
    page.get_by_role('button',name='+ Ajouter une partie',exact=True).click()
    page.get_by_label('Nom de la partie',exact=True).fill('AMRAP B')
    page.get_by_label('Durée / time cap de la partie (min)',exact=True).fill('8')
    exercise('pompe')
    page.get_by_role('button',name='Monter la partie',exact=True).click()
    page.get_by_role('button',name='Descendre la partie',exact=True).click()
    page.get_by_role('button',name='1. Partie 1',exact=False).click()
    page.get_by_label('Nom de la partie',exact=True).fill('Force')
    expect(page.locator('.prescription')).to_have_count(1)
    with page.expect_response(lambda r: r.url.endswith('/api/cycles') and r.request.method=='POST') as result:
        page.get_by_role('button',name='Enregistrer le bloc',exact=True).click()
    assert result.value.status==201,result.value.text()
    source=result.value.json(); session=source['weeks'][0]['sessions'][0]
    assert [x['title'] for x in session['parts']]==['Force','AMRAP A','AMRAP B']
    assert len(session['exercises'])==3
    assert len(set(e['exerciseId'] for e in session['exercises']))==3
    page.screenshot(path=str(OUT/'composition-pc.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    auth=context.request.get(BASE+'/api/auth/session').json()
    headers={'X-CSRF-TOKEN':auth['csrfToken'],'X-Training-User':auth['user']['id']}
    target={**source,'name':'Bloc destinataire','durationWeeks':3,'startDate':'2026-12-01','weeks':[{'number':i+1,'focus':'Conserver','notes':'','deload':i==2,'sessions':[]} for i in range(3)]}
    response=context.request.post(BASE+'/api/cycles',data=target,headers=headers); assert response.status==201,response.text()
    target=response.json()
    page.get_by_role('button',name='Retour',exact=True).click(); page.reload()
    page.locator('.block-card').filter(has_text='Force et deux AMRAP').get_by_role('button',name='Copier vers un autre bloc').click()
    page.get_by_label('Bloc destinataire',exact=True).select_option(target['id'])
    expect(page.get_by_role('button',name='Copier et enregistrer',exact=True)).to_be_disabled()
    page.get_by_label('Je confirme le remplacement des séances prévues.').check()
    page.screenshot(path=str(OUT/'copie-pc.png'),full_page=True)
    with page.expect_response(lambda r: r.url.endswith('/api/cycles/'+target['id']) and r.request.method=='PUT') as result:
        page.get_by_role('button',name='Copier et enregistrer',exact=True).click()
    assert result.value.status==200,result.value.text()
    saved=result.value.json(); assert saved['startDate']=='2026-12-01' and saved['weeks'][2]['deload']
    ids=[]
    for week in saved['weeks']:
        s=week['sessions'][0]; ids += [s['id']]+[x['id'] for x in s['parts']]+[e['id'] for e in s['exercises']]
        assert [x['title'] for x in s['parts']]==['Force','AMRAP A','AMRAP B']
        assert [e['partId'] for e in s['exercises']]==[x['id'] for x in s['parts']]
    assert len(ids)==len(set(ids))
    mobile=authenticated_context(browser,BASE,profile=True,viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    phone=mobile.new_page(); phone.on('pageerror',lambda e: errors.append(str(e)))
    phone.goto(BASE+'/#seance'); phone.locator('.workout-picker select').nth(0).select_option(target['id'])
    phone.get_by_role('button',name='Commencer la séance',exact=True).click()
    expect(phone.locator('.workout-part')).to_have_count(3)
    expect(phone.locator('.workout-part').nth(1)).to_contain_text('AMRAP A · AMRAP · 12 min')
    row=phone.locator('.set-row').first; row.locator('input').first.fill('8'); row.get_by_role('button').click()
    with phone.expect_response(lambda r: '/api/workouts/' in r.url and r.request.method=='PUT') as result:
        phone.get_by_role('button',name='Enregistrer',exact=True).click()
    assert result.value.status==200,result.value.text()
    assert len(result.value.json()['plannedSession']['parts'])==3
    phone.reload(); expect(phone.locator('.workout-part')).to_have_count(3)
    phone.screenshot(path=str(OUT/'parties-mobile.png'),full_page=True)
    for width in [390,320]:
        phone.set_viewport_size({'width':width,'height':844})
        assert phone.evaluate('document.documentElement.scrollWidth <= innerWidth'),str(width)
    assert not errors,errors
    browser.close()
print('OK : composition force + 2 AMRAP, copie vers 3 semaines, identifiants indépendants, saisie et reprise mobile, sans débordement ni erreur JS.')
