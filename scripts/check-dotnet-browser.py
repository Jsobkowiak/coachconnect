"""Real React/.NET journey: desktop programme, mobile performance and reload recovery."""
import json
import os
from pathlib import Path
import secrets
from training_test_auth import authenticated_context
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('TRAINING_URL', 'http://localhost:8081')
OUT = Path(__file__).resolve().parent.parent / '.local' / 'training-qa'
OUT.mkdir(parents=True, exist_ok=True)
name = 'QA bloc ' + secrets.token_hex(4)
cycle_id = workout_id = None
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    desktop = authenticated_context(browser, BASE, profile=True, viewport={'width': 1536, 'height': 1000})
    desktop.add_init_script("localStorage.setItem('coachconnect-theme', 'dark')")
    page = desktop.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(BASE)
        page.get_by_role('button', name='+ Créer un bloc', exact=True).click()
        page.get_by_label('Nom du bloc', exact=True).fill(name)
        page.get_by_label('Durée (semaines)', exact=True).fill('2')
        page.get_by_label('Objectif', exact=True).fill('Tractions en volume et progression au bench')
        page.get_by_role('button', name='+ Séance', exact=True).click()
        page.get_by_label('Nom de la séance', exact=True).fill('Haut du corps')
        page.get_by_role('button', name='+ Ajouter un exercice', exact=True).click()
        page.get_by_label('Rechercher un exercice', exact=True).fill(os.environ.get('CATALOG_QA_QUERY', 'traction'))
        page.get_by_role('button', name='Ajouter à la séance', exact=True).first.click()
        page.get_by_label('Charge (kg)', exact=True).fill('10')
        page.once('dialog', lambda dialog: dialog.accept('2'))
        page.get_by_role('button', name='Copier la semaine', exact=True).click()
        with page.expect_response(lambda r: r.url.endswith('/api/cycles') and r.request.method == 'POST') as response:
            page.get_by_role('button', name='Enregistrer le bloc', exact=True).click()
        result = response.value.json()
        assert response.value.status == 201, result
        cycle_id = result['id']
        expected_exercise = os.environ.get('CATALOG_QA_EXERCISE')
        if expected_exercise:
            snapshot = result['weeks'][0]['sessions'][0]['exercises'][0]['snapshot']
            assert snapshot['name'] == expected_exercise, snapshot['name']
            assert snapshot['media']['license']['ai_generated']
        assert len(result['weeks']) == 2
        assert result['weeks'][0]['sessions'][0]['id'] != result['weeks'][1]['sessions'][0]['id']
        expect(page.get_by_text('Bloc enregistré · les performances restent dans le carnet de séance.', exact=True)).to_be_visible()
        page.screenshot(path=str(OUT / 'dotnet-blocs-pc.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.get_by_role('button', name='Retour', exact=True).click()
        page.get_by_role('button', name='Brouillons', exact=True).click()
        expect(page.locator('.block-card').filter(has_text=name)).to_be_visible()
        page.get_by_role('button', name='Archivés', exact=True).click()
        expect(page.locator('.block-card').filter(has_text=name)).to_have_count(0)
        page.get_by_role('button', name='Tous', exact=True).click()
        page.screenshot(path=str(OUT / 'refonte-blocs-pc.png'), full_page=True)
        expect(page.get_by_role('button', name='Activer le thème sombre', exact=True)).to_have_count(0)
        expect(page.locator('html')).to_have_attribute('data-theme', 'light')
        page.get_by_role('navigation').get_by_role('button', name='Ma séance', exact=True).click()
        expect(page.get_by_role('heading', name='Ma séance', exact=True)).to_be_visible()
        mobile = authenticated_context(browser, BASE, profile=True, viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        phone = mobile.new_page()
        phone.on('pageerror', lambda error: errors.append(str(error)))
        phone.goto(BASE + '/#seance')
        phone.locator('.workout-picker select').nth(0).select_option(cycle_id)
        phone.get_by_role('button', name='Commencer la séance', exact=True).click()
        rows = phone.locator('.set-row')
        rows.first.get_by_role('button').click()
        expect(phone.get_by_role('alert')).to_have_text('Renseigne la performance avant de valider la série.')
        rows.nth(0).locator('input').nth(0).fill('8')
        rows.nth(0).locator('input').nth(1).fill('12.5')
        rows.nth(0).get_by_role('button').click()
        rows.nth(1).locator('input').nth(0).fill('7')
        rows.nth(1).get_by_role('button').click()
        expect(phone.locator('.new-record')).to_contain_text('12,5 kg × 8 rép.')
        with phone.expect_response(lambda r: '/api/workouts/' in r.url and r.request.method == 'PUT') as response:
            phone.get_by_role('button', name='Enregistrer', exact=True).click()
        record = response.value.json()
        assert response.value.status == 200, record
        workout_id = record['id']
        assert record['exercises'][0]['sets'][0]['loadKg'] == 12.5
        assert record['plannedSession']['exercises'][0]['loadKg'] == 10
        expect(phone.get_by_text('Enregistré', exact=True)).to_be_visible()
        expect(phone.locator('.personal-record > strong')).to_contain_text('12,5 kg')
        expect(phone.locator('.new-record')).to_have_count(0)
        phone.evaluate('window.scrollTo(0, 0)')
        phone.screenshot(path=str(OUT / 'dotnet-seance-mobile.png'), full_page=True)
        assert phone.evaluate('document.documentElement.scrollWidth <= innerWidth')
        phone.reload()
        expect(phone.get_by_role('heading', name='Haut du corps', exact=True)).to_be_visible()
        expect(phone.locator('.set-row').first.locator('input').first).to_have_value('8')
        phone.set_viewport_size({'width': 320, 'height': 740})
        assert phone.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Débordement sur écran 320px'
        phone.set_viewport_size({'width': 390, 'height': 844})
        with phone.expect_response(lambda r: '/api/workouts/' in r.url and r.request.method == 'PUT') as response:
            phone.get_by_role('button', name='Terminer', exact=True).click()
        assert response.value.status == 200, response.value.text()
        expect(phone.get_by_text('Séance terminée', exact=True)).to_be_visible()
        phone.get_by_role('button', name='Retour aux séances', exact=True).click()
        assert not errors, errors
        print('OK: blocs PC, copie indépendante, catalogue, performances mobile, repos, reprise après rechargement, sauvegarde et finalisation. Aucune erreur JS.')
    finally:
        for kind, identifier in [('workouts', workout_id), ('cycles', cycle_id)]:
            if identifier:
                response = desktop.request.get(BASE + '/api/' + kind + '/' + identifier)
                if response.ok:
                    revision = response.json()['revision']
                    desktop.request.delete(BASE + '/api/' + kind + '/' + identifier + '?revision=' + str(revision))
        browser.close()
