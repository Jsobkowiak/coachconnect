"""Integrated screens, recovery and switching accounts on PC/mobile. QA only."""
import os,json,secrets,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
BASE=os.environ['ACCOUNTS_TEST_URL'];assert ':18081' in BASE
OUT=Path('.local/accounts-qa');runtime=json.loads((OUT/'runtime.json').read_text());assert runtime['db'].startswith('coachconnect_accounts_test_')
owner=json.loads((OUT/'owner.json').read_text());legacy=json.loads((OUT/'claim-before.json').read_text());token=(OUT/'owner-token').read_text().strip()
# Make only the original QA owner's fixtures legacy again. Other test accounts remain untouched.
owner_id=owner['userId'];assert len(owner_id)==36
keys={'training_profiles':('id',legacy['/profile']['profile']['id']),'training_cycles':('id',legacy['/cycles'][0]['id']),'training_workouts':('id',legacy['/workouts'][0]['id']),'training_nutrition_settings':('cycle_id',legacy['/cycles'][0]['id'])}
sql=';'.join("UPDATE "+table+" SET owner_id=NULL WHERE "+key+"='"+value+"'" for table,(key,value) in keys.items())+'; UPDATE training_account_setup SET owner_id=NULL,claimed_at=NULL;'

subprocess.run(['docker','compose','--profile','catalog','--profile','training','exec','-T','training-db','psql','-U','training','-d',runtime['db'],'-c',sql],check=True,capture_output=True)
email='browser-'+secrets.token_hex(10)+'@example.test';password='Private browser passphrase '+secrets.token_hex(12)
other_email='other-'+secrets.token_hex(10)+'@example.test';other_password='Other browser passphrase '+secrets.token_hex(12)
with sync_playwright() as p:
 b=p.chromium.launch();context=b.new_context(viewport={'width':1440,'height':1000});pc=context.new_page();errors=[];pc.on('pageerror',lambda e:errors.append(str(e)))
 old_draft={'workout':legacy['/workouts'][0],'dirty':False}
 context.add_init_script('if(!sessionStorage.getItem("qa-draft-seeded")){localStorage.setItem("coachconnect-workout-draft",'+json.dumps(json.dumps(old_draft))+');sessionStorage.setItem("qa-draft-seeded","1");}')
 pc.goto(BASE+'/#initialisation='+token)
 expect(pc.get_by_role('heading',name='Créer mon compte',exact=True)).to_be_visible()
 assert token not in pc.url,'Recovery code must be removed from the visible URL'
 assert pc.locator('.main-navigation').count()==0
 pc.get_by_label('Adresse e-mail',exact=True).fill(email);pc.get_by_label('Mot de passe',exact=True).fill(password)
 pc.get_by_label('Confirmer le mot de passe',exact=True).fill(password+'no')
 pc.get_by_role('button',name='Créer mon compte',exact=True).click();expect(pc.get_by_role('alert')).to_have_text('Les deux mots de passe doivent être identiques.')
 pc.get_by_label('Confirmer le mot de passe',exact=True).fill(password);pc.screenshot(path=str(OUT/'register-pc.png'),full_page=True)
 pc.get_by_role('button',name='Créer mon compte',exact=True).click()
 expect(pc.get_by_role('heading',name='Retrouver tes données',exact=True)).to_be_visible()
 pc.get_by_role('button',name='Récupérer mes données et continuer',exact=True).click()
 expect(pc.get_by_role('button',name='Mon compte',exact=True)).to_be_visible()
 state=context.request.get(BASE+'/api/auth/session').json();uid=state['user']['id'];assert state['user']['ownsLegacyData']
 assert context.request.get(BASE+'/api/profile').json()['profile']==legacy['/profile']['profile']
 assert pc.evaluate('localStorage.getItem("coachconnect-workout-draft")') is None
 assert pc.evaluate('(id)=>!!localStorage.getItem("coachconnect-workout-draft:"+id)',uid)
 # A new dirty workout draft stays scoped to this user after signing out.
 pc.evaluate('(id)=>localStorage.removeItem("coachconnect-workout-draft:"+id)',uid)
 pc.get_by_role('button',name='Ma séance',exact=True).click()
 pc.get_by_role('button',name='Commencer la séance',exact=True).click()
 pc.locator('.set-row').first.locator('input').first.fill('9')
 pc.get_by_role('button',name='Mon compte',exact=True).click()
 expect(pc.get_by_role('dialog',name='Mon compte')).to_contain_text(email)
 pc.once('dialog',lambda d:d.accept());pc.get_by_role('button',name='Me déconnecter',exact=True).click()
 expect(pc.get_by_role('heading',name='Me connecter',exact=True)).to_be_visible()
 assert pc.locator('.workout-page').count()==0
 pc.get_by_role('button',name='Créer un compte',exact=True).click()
 pc.get_by_label('Adresse e-mail',exact=True).fill(other_email);pc.get_by_label('Mot de passe',exact=True).fill(other_password);pc.get_by_label('Confirmer le mot de passe',exact=True).fill(other_password)
 pc.get_by_role('button',name='Créer mon compte',exact=True).click()
 expect(pc.get_by_role('heading',name='Commençons par ton profil sportif',exact=True)).to_be_visible()
 assert context.request.get(BASE+'/api/cycles').json()==[] and context.request.get(BASE+'/api/profile').json()['profile'] is None
 assert pc.locator('.workout-page').count()==0
 pc.get_by_role('button',name='Mon compte',exact=True).click();pc.get_by_role('button',name='Me déconnecter',exact=True).click()
 expect(pc.get_by_role('heading',name='Me connecter',exact=True)).to_be_visible()
 pc.get_by_label('Adresse e-mail',exact=True).fill(email);pc.get_by_label('Mot de passe',exact=True).fill(password);pc.get_by_role('button',name='Me connecter',exact=True).click()
 pc.get_by_role('button',name='Ma séance',exact=True).click();expect(pc.locator('.set-row').first.locator('input').first).to_have_value('9')
 # A second device can sign in, change the password and revoke the first device's session.
 phone_context=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);phone=phone_context.new_page();phone.on('pageerror',lambda e:errors.append(str(e)))
 phone.goto(BASE+'/login');expect(phone.get_by_role('heading',name='Me connecter',exact=True)).to_be_visible()
 for width in [390,320]:
  phone.set_viewport_size({'width':width,'height':844});assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
 phone.screenshot(path=str(OUT/'login-mobile.png'),full_page=True)
 phone.get_by_label('Adresse e-mail',exact=True).fill(email);phone.get_by_label('Mot de passe',exact=True).fill(password);phone.get_by_role('button',name='Me connecter',exact=True).click()
 expect(phone.get_by_role('button',name='Mon compte',exact=True)).to_be_visible();assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth')
 phone.get_by_role('button',name='Mon compte',exact=True).click();dialog=phone.get_by_role('dialog',name='Mon compte')
 dialog.get_by_text('Changer mon mot de passe',exact=True).click()
 phone.screenshot(path=str(OUT/'account-mobile.png'),full_page=True)
 new_password='New private browser phrase '+secrets.token_hex(12)
 dialog.get_by_label('Mot de passe actuel',exact=True).fill(password);dialog.get_by_label('Nouveau mot de passe',exact=True).fill(new_password);dialog.get_by_label('Confirmer le nouveau mot de passe',exact=True).fill(new_password)
 dialog.get_by_role('button',name='Enregistrer le nouveau mot de passe',exact=True).click()
 expect(phone.get_by_role('heading',name='Me connecter',exact=True)).to_be_visible()
 # A protected API call in the old PC session clears the old interface.
 pc.once('dialog',lambda d:d.accept());pc.get_by_role('button',name='Stats',exact=True).click()
 expect(pc.get_by_role('heading',name='Me connecter',exact=True)).to_be_visible()
 phone.get_by_label('Adresse e-mail',exact=True).fill(email);phone.get_by_label('Mot de passe',exact=True).fill(new_password);phone.get_by_label('Rester connecté sur cet appareil',exact=True).check();phone.get_by_role('button',name='Me connecter',exact=True).click()
 expect(phone.get_by_role('button',name='Mon compte',exact=True)).to_be_visible();phone.reload();expect(phone.get_by_role('button',name='Mon compte',exact=True)).to_be_visible()
 phone.get_by_role('button',name='Mon compte',exact=True).click();phone.keyboard.press('Escape');expect(phone.get_by_role('dialog')).to_have_count(0)
 assert not errors,errors
 b.close()
print('OK : inscription/confirmation, récupération explicite et brouillon historique, logout, comptes isolés sur le même appareil, reprise du brouillon, connexion mobile 320px, changement de mot de passe, révocation interappareils et persistance.')
