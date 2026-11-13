import copy
import hashlib
import xml.etree.ElementTree as ET
import json
from importlib.resources import files

import pytest
from fastapi.testclient import TestClient

from exercise_catalog import api
from exercise_catalog.editorial import EditorialEntry, active_documents, publish_seed
from exercise_catalog.media import effective_hash
from exercise_catalog.pipeline import process_records


def test_authored_seed_has_complete_unique_french_entries():
    seed=json.loads(files('exercise_catalog').joinpath('data/catalogue-fr.json').read_text())
    entries=[EditorialEntry.model_validate(row) for row in seed['entries']]
    assert len(entries)>=70
    assert len({row.key for row in entries})==len(entries)
    for row in entries:
        if row.diagram:
            payload=files('exercise_catalog').joinpath('data/diagrams/'+row.diagram).read_bytes()
            assert hashlib.sha256(payload).hexdigest()==row.diagram[:64]
            svg=ET.fromstring(payload)
            assert all(element.tag.split('}')[-1] in {'svg','style','rect','text','g','path','circle'} for element in svg.iter())
            assert b'<script' not in payload and b'href=' not in payload
    for row in entries:
        if row.key in {'parallel-bar-dips','barbell-push-press','pike-push-up'}:
            assert row.authored_on.isoformat()=='2026-10-16'
    assert all(row.data.language=='fr' for row in entries)
    assert all(len(row.data.instructions)>=3 and len(row.data.common_mistakes)>=1 for row in entries)
    bicycle=next(row for row in entries if row.reference_key=='free-exercise-db:Air_Bike')
    assert bicycle.data.name=='Crunch vélo au sol'
    assert 'sans vélo' in bicycle.data.description
    goblet=next(row for row in entries if row.reference_key=='free-exercise-db:Goblet_Squat')
    assert goblet.data.equipment=='kettlebells'
    assert 'kettlebell' in goblet.data.name


@pytest.mark.integration
def test_french_publication_atomic_replay_search_and_independence(database,record,metadata,monkeypatch):
    db,config=database
    process_records(db,[record],metadata,'raw')
    source=db.exercises.find_one()
    entry={
        'key':'squat-arriere','reference_key':source['source_key'],'reference_hash':effective_hash(source),
        'data':{**source['source_data'],'language':'fr','name':'Squat arrière à la barre',
                'aliases':['Barbell Squat'],'instructions':['Place les pieds.','Fléchis les jambes.','Reviens debout.'],
                'description':'Squat avec la barre sur le haut du dos.',
                'common_mistakes':['Laisser les genoux rentrer.'],'required_equipment':['Barre']},
        'media_note':'Aucun visuel retenu pour cette fixture.', 'references':['https://example.test/source'],
    }
    entry['authored_on']='2026-10-16'
    seed={'version':'test.1','authored_on':'2026-10-11','entries':[entry]}
    initial=publish_seed(db,config,seed)
    assert publish_seed(db,config,seed)==initial
    assert db.curated_exercises.count_documents({})==1
    assert db.curated_exercises.find_one()['provenance']['authored_on']=='2026-10-16'
    assert db.exercises.find_one()['source_data']['language']=='en'
    broken=copy.deepcopy(seed);broken['entries'].append({**entry,'key':'invalid','reference_hash':'changed'})
    with pytest.raises(ValueError):publish_seed(db,config,broken)
    assert len(active_documents(db))==1
    monkeypatch.setattr(api,'settings',lambda:config)
    with TestClient(api.app) as client:
        for query in ['arriere','Barbell Squat']:
            response=client.get('/exercises',params={'q':query}).json()
            assert response['total']==1
            assert response['items'][0]['language']=='fr'
            assert response['items'][0]['id']==source['_id']
        assert client.get('/exercises?catalog=source').json()['items'][0]['language']=='en'
        assert client.get('/exercises/'+source['_id']).json()['name']=='Squat arrière à la barre'
        assert client.get('/media-coverage').json()['total']==1
        # An external import updates raw data without rewriting the authored French revision.
        record['name']='Updated English Squat'
        process_records(db,[record],metadata,'fresh-source')
        assert client.get('/exercises/'+source['_id']).json()['name']=='Squat arrière à la barre'
        assert client.get('/exercises?catalog=source').json()['items'][0]['name']=='Updated English Squat'


def test_original_raster_illustrations_are_valid_and_available(monkeypatch, tmp_path):
    from io import BytesIO
    from types import SimpleNamespace
    from PIL import Image
    from exercise_catalog import editorial
    seed=json.loads(files('exercise_catalog').joinpath('data/catalogue-fr.json').read_text())
    entries=[row for row in seed['entries'] if row['key'] in {'barbell-push-press','pike-push-up'}]
    assert len(entries)==2
    for row in seed['entries']:
        entry=EditorialEntry.model_validate(row)
        assert len(entry.illustrations)==1
        filename=entry.illustrations[0]
        path=files('exercise_catalog').joinpath('data/illustrations/'+filename)
        payload=path.read_bytes()
        assert hashlib.sha256(payload).hexdigest()==filename[:64]
        assert len(payload)<=2_000_000
        with Image.open(BytesIO(payload)) as image:
            assert image.format=='PNG'
            assert image.width<=4096 and image.height<=4096
            image.verify()
        response=api.get_media_asset(filename)
        assert response.media_type=='image/png'
        assert str(response.path)==str(path)
    prepared=editorial.prepare_entries(None,SimpleNamespace(media_directory=tmp_path),{**seed,'entries':entries})
    assert all(row['media']['license']['ai_generated'] for row in prepared)
    # A changed file with an unchanged filename must never be published.
    folder=tmp_path/'data'/'illustrations';folder.mkdir(parents=True)
    (folder/entries[0]['illustrations'][0]).write_bytes(b'changed-content')
    monkeypatch.setattr(editorial,'files',lambda package:tmp_path)
    with pytest.raises(ValueError,match='Missing or corrupted asset'):
        editorial.prepare_entries(None,SimpleNamespace(media_directory=tmp_path),{**seed,'entries':entries[:1]})


@pytest.mark.integration
def test_original_artwork_preserves_source_identity_and_old_revision(database, record, metadata):
    db, config = database
    process_records(db, [record], metadata, 'artwork-identity')
    source = db.exercises.find_one()
    seed = json.loads(files('exercise_catalog').joinpath('data/catalogue-fr.json').read_text())
    entry = copy.deepcopy(next(e for e in seed['entries'] if e['key'] == 'barbell-push-press'))
    entry.update(reference_key=source['source_key'], reference_hash=effective_hash(source))
    old_entry = copy.deepcopy(entry)
    old_entry.pop('illustrations')
    original = {'version': 'identity-before', 'authored_on': seed['authored_on'], 'entries': [old_entry]}
    publish_seed(db, config, original)
    old_document = active_documents(db)[0]
    updated = {**original, 'version': 'identity-after', 'entries': [entry]}
    publish_seed(db, config, updated)
    current = active_documents(db)[0]
    assert current['exercise_id'] == old_document['exercise_id'] == source['_id']
    assert current['data'] == old_document['data']
    assert current['media']['license']['ai_generated'] is True
    assert db.curated_exercises.find_one({'_id': old_document['_id']}) == old_document
    assert db.exercises.find_one() == source
    # Multiple alternative artwork providers are ambiguous and must fail validation.
    with pytest.raises(ValueError, match='one illustration provider'):
        EditorialEntry.model_validate({**entry, 'diagram': 'a' * 64 + '.svg'})
