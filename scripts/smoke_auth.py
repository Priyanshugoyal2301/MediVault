"""Live API/database MFA verification using a disposable synthetic account."""
import hashlib
import time
import uuid
import bootstrap_imports  # noqa: F401

import httpx

from smoke_local import BASE, ORIGIN, check, database_connection


def main():
    # Import package aliases registered by the repository's packages initializer.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from services.auth_service.core.mfa import code_at

    email = f'mfa-smoke-{uuid.uuid4().hex}@example.com'
    password = 'Synthetic-security-check-only!'
    with httpx.Client(base_url=BASE, headers={'Origin': ORIGIN}, timeout=30) as client:
        check(client.post('/auth/register', json={'email': email, 'password': password}), 201)
        user_id = check(client.get('/auth/me'), 200)['id']
        secret = check(client.post('/auth/mfa/setup', json={'password': password}), 200)['secret']
        code = code_at(secret, int(time.time() // 30))
        recovery = check(client.post('/auth/mfa/enable', json={'password': password, 'code': code}), 200)['recovery_codes']
        assert check(client.get('/auth/me'), 200)['mfa_enabled']
        with database_connection() as connection, connection.cursor() as cursor:
            cursor.execute('SELECT otp_secret, otp_recovery, hashed_password FROM users WHERE id = %s', (user_id,))
            encrypted, hashes, password_hash = cursor.fetchone()
            assert secret not in encrypted and encrypted.startswith('MEDIVAULT-ENC-1\n')
            assert password_hash != password and hashlib.sha256(recovery[0].encode()).hexdigest() in hashes
            assert recovery[0] not in hashes
        check(client.post('/auth/logout'), 204)
        credentials = {'email': email, 'password': password}
        challenge = client.post('/auth/login', json=credentials)
        check(challenge, 401)
        assert challenge.headers.get('X-MFA-Required') == 'true'
        incorrect = client.post('/auth/login', json={**credentials, 'password': 'wrong'})
        check(incorrect, 401)
        assert 'X-MFA-Required' not in incorrect.headers
        check(client.post('/auth/login', json={**credentials, 'verification_code': code}), 401)
        check(client.post('/auth/login', json={**credentials, 'verification_code': recovery[0]}), 200)
        check(client.post('/auth/login', json={**credentials, 'verification_code': recovery[0]}), 401)
        old_cookie = client.cookies.get('medivault_session')
        check(client.post('/auth/mfa/disable', json={'password': password, 'code': recovery[1]}), 204)
        check(httpx.get(BASE + '/auth/me', headers={'Cookie': f'medivault_session={old_cookie}'}), 401)
        check(client.post('/auth/login', json=credentials), 200)
        assert not check(client.get('/auth/me'), 200)['mfa_enabled']
        for _ in range(8):
            check(client.post('/auth/login', json={'email': email, 'password': 'incorrect'}), 401)
        check(client.post('/auth/login', json=credentials), 429)
        with database_connection() as connection, connection.cursor() as cursor:
            cursor.execute('SELECT auth_failures FROM users WHERE id = %s', (user_id,))
            assert cursor.fetchone()[0] == 8
        print('PASS: encrypted MFA secret, hashed password/recovery codes, replay denial, single-use recovery, session revocation and persisted attempt limit')


if __name__ == '__main__':
    main()
