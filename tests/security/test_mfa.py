from services.auth_service.core.mfa import code_at, consume_recovery, new_secret, recovery_codes, verify_code


def test_rfc6238_vector_and_replay_prevention():
    # RFC 6238 SHA-1 test secret at t=59: eight-digit 94287082 -> six-digit 287082.
    secret="GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert code_at(secret,1)=="287082"
    assert verify_code(secret,"287082",timestamp=59)==1
    assert verify_code(secret,"287082",last_counter=1,timestamp=59) is None
    assert verify_code(secret,"287082",timestamp=180) is None
    assert verify_code(secret,"wrong",timestamp=59) is None


def test_recovery_codes_are_random_hashed_and_single_use():
    plain,hashes=recovery_codes()
    assert len(set(plain))==8
    assert not set(plain)&set(hashes)
    remaining=consume_recovery(hashes,plain[0])
    assert len(remaining)==7
    assert consume_recovery(remaining,plain[0]) is None
    assert consume_recovery(hashes,"incorrect") is None
    assert new_secret()!=new_secret()
