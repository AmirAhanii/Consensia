from datetime import datetime, timedelta, timezone
from hashlib import sha256
import random
import jwt
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hasher.verify(password, hashed)


def create_access_token(subject: str, secret: str, expires_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def new_email_verification_code() -> tuple[str, str]:
    raw_code = f"{random.SystemRandom().randint(0, 999999):06d}"
    code_hash = sha256(raw_code.encode("utf-8")).hexdigest()
    return raw_code, code_hash


def hash_verification_code(raw_code: str) -> str:
    return sha256(raw_code.strip().encode("utf-8")).hexdigest()


def decode_access_token(token: str, secret: str) -> str:
    payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    return str(payload["sub"])