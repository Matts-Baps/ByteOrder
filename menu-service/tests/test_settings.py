"""
Tests for the /settings/ endpoints.

Key property under test: settings are fully isolated per kitchen_id —
writing for kitchen A must never affect kitchen B and vice versa.
This directly covers the "Matt's Baps / Dash0 Kitchen bleed-through" bug.
"""
import pytest
from app import models


# ── Basic CRUD ────────────────────────────────────────────────────────────────

def test_list_settings_empty_for_new_kitchen(client):
    res = client.get('/settings/')
    assert res.status_code == 200
    assert res.json() == []


def test_upsert_setting_creates_and_returns(client):
    res = client.put('/settings/kitchen_name', json={'value': 'My Kitchen'})
    assert res.status_code == 200
    data = res.json()
    assert data['key'] == 'kitchen_name'
    assert data['value'] == 'My Kitchen'


def test_get_setting_returns_stored_value(client):
    client.put('/settings/kitchen_name', json={'value': 'My Kitchen'})
    res = client.get('/settings/kitchen_name')
    assert res.status_code == 200
    assert res.json()['value'] == 'My Kitchen'


def test_get_missing_setting_returns_null(client):
    res = client.get('/settings/kitchen_name')
    assert res.status_code == 200
    assert res.json()['value'] is None


def test_upsert_setting_overwrites_existing(client):
    client.put('/settings/kitchen_name', json={'value': 'Old Name'})
    client.put('/settings/kitchen_name', json={'value': 'New Name'})
    res = client.get('/settings/kitchen_name')
    assert res.json()['value'] == 'New Name'


def test_list_settings_returns_all_keys_for_kitchen(client):
    client.put('/settings/kitchen_name', json={'value': 'My Kitchen'})
    client.put('/settings/brand_primary', json={'value': '#ff0000'})
    res = client.get('/settings/')
    assert res.status_code == 200
    keys = {s['key'] for s in res.json()}
    assert 'kitchen_name' in keys
    assert 'brand_primary' in keys


def test_unknown_key_rejected_on_upsert(client):
    res = client.put('/settings/not_a_real_key', json={'value': 'x'})
    assert res.status_code == 400


# ── Isolation ─────────────────────────────────────────────────────────────────

def test_other_kitchen_settings_not_visible(client, db):
    """Settings seeded for a different kitchen must not appear for test-kitchen."""
    db.add(models.Setting(kitchen_id='other-kitchen', key='kitchen_name', value="Other's Kitchen"))
    db.commit()

    # client is scoped to 'test-kitchen'
    res = client.get('/settings/kitchen_name')
    assert res.json()['value'] is None


def test_other_kitchen_not_included_in_list(client, db):
    """GET /settings/ must only return rows for the active kitchen."""
    db.add(models.Setting(kitchen_id='other-kitchen', key='kitchen_name', value="Other's Kitchen"))
    db.commit()

    res = client.get('/settings/')
    assert res.json() == []


def test_matts_baps_dash0_kitchen_scenario(client, db):
    """
    Regression test for the shared-settings bug:
      User 1 (kitchen-a) sets name 'Matt's Baps'.
      User 2 (test-kitchen) sets name 'Dash0 Kitchen'.
      User 1 must still see 'Matt's Baps', not 'Dash0 Kitchen'.
    """
    # Seed kitchen-a's data directly (simulates User 1's prior save)
    db.add(models.Setting(kitchen_id='kitchen-a', key='kitchen_name', value="Matt's Baps"))
    db.add(models.Setting(kitchen_id='kitchen-a', key='brand_primary', value='#477e9a'))
    db.commit()

    # User 2 (test-kitchen) writes their own settings via the API
    client.put('/settings/kitchen_name', json={'value': 'Dash0 Kitchen'})
    client.put('/settings/brand_primary', json={'value': '#ff0000'})

    # kitchen-a's rows must be completely unchanged
    db.expire_all()
    a_name = db.query(models.Setting).filter_by(
        kitchen_id='kitchen-a', key='kitchen_name'
    ).first()
    a_colour = db.query(models.Setting).filter_by(
        kitchen_id='kitchen-a', key='brand_primary'
    ).first()
    assert a_name.value == "Matt's Baps"
    assert a_colour.value == '#477e9a'

    # test-kitchen sees only its own data
    res = client.get('/settings/kitchen_name')
    assert res.json()['value'] == 'Dash0 Kitchen'
