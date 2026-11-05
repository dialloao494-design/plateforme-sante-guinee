"""Clinic policy must not break login or allow writes from before a reset."""
import json
import uuid
import pytest
import models
from security import create_access_token
from schemas.platform import PlatformClinicConfigurationUpdate
from services.platform_admin_service import clinic_configuration
from services.client_request_idempotency import hash_request_body


def setup_clinic(db, user, config):
    clinic = models.Clinic(name='Offline policy regression', city='Conakry', is_active=True,
                           configuration_json=json.dumps(config))
    db.add(clinic)
    db.commit()
    user.clinic_id = clinic.id
    db.commit()
    token = create_access_token({'sub': user.email, 'user_id': user.id, 'role': user.role,
                                 'session_version': user.session_version, 'tv': user.token_version or 0})
    return clinic, {'Authorization': f'Bearer {token}'}


@pytest.mark.parametrize('config', [
    {'data_retention_days': None, 'trusted_workstation_days': None, 'offline_workstations_enabled': False},
    {'data_retention_days': 'bad', 'offline_data_epoch': None},
    [], 'invalid',
])
def test_auth_profile_is_independent_of_unrelated_bad_settings(client, db_session, admin_user, config):
    _, headers = setup_clinic(db_session, admin_user, config)
    response = client.get('/auth/me', headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()['offline_data_epoch'] == 1
    if isinstance(config, dict) and config.get('offline_workstations_enabled') is False:
        assert response.json()['offline_workstations_enabled'] is False


def test_nullable_settings_normalize_without_crashing(client, db_session, admin_user):
    payload = PlatformClinicConfigurationUpdate(data_retention_days=None, trusted_workstation_days=None).model_dump(exclude_unset=True)
    clinic, _ = setup_clinic(db_session, admin_user, payload)
    configuration = clinic_configuration(clinic)
    assert configuration['data_retention_days'] == 3650
    assert configuration['trusted_workstation_days'] == 30


@pytest.mark.parametrize('epoch', [None, '1', 'invalid', '3'])
def test_reset_rejects_stale_writes_before_idempotent_replay(client, db_session, admin_user, epoch):
    clinic, headers = setup_clinic(db_session, admin_user, {'offline_data_epoch': 2})
    request_id = str(uuid.uuid4())
    path = '/clinical/reception/his/patients'
    db_session.add(models.ApiClientIdempotencyKey(client_request_id=request_id, method='POST', path=path,
        request_hash=hash_request_body(b'{}'), status_code=200, response_body='{"id":999}',
        user_id=admin_user.id, clinic_id=clinic.id))
    db_session.commit()
    headers.update({'X-Client-Request-Id': request_id, 'X-Record-Version': '1', 'Content-Type': 'application/json'})
    if epoch is not None:
        headers['X-Offline-Data-Epoch'] = epoch
    response = client.post(path, content=b'{}', headers=headers)
    assert response.status_code == 409, response.text
    assert response.json()['detail']['code'] == 'offline_epoch_mismatch'
    headers['X-Offline-Data-Epoch'] = '2'
    assert client.post(path, content=b'{}', headers=headers).json() == {'id': 999}


def test_epoch_is_scoped_to_current_clinic(client, db_session, admin_user):
    _, headers = setup_clinic(db_session, admin_user, {'offline_data_epoch': 1})
    other = models.Clinic(name='Other clinic reset', city='Conakry', is_active=True,
                          configuration_json='{"offline_data_epoch":9}')
    db_session.add(other)
    db_session.commit()
    response = client.post('/clinical/reception/his/patients', json={}, headers=headers)
    assert response.status_code == 422, response.text
