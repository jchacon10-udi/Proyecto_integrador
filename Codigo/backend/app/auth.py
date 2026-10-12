"""Sesión opaca DEMO; no autenticación de producción ni cuentas Oracle."""
import hashlib
import hmac
import secrets
import time
from threading import RLock
from .domain import Session, ROLES

class AuthService:
    def __init__(self, clock=time.monotonic):
        self.clock=clock
        self.lock=RLock()
        self.sessions: dict[str, tuple[Session,float]]={}
        self.password_hash=hashlib.scrypt(b"enph-demo",salt=b"enph-public-demo",n=16384,r=8,p=1)
        self.users={name:Session(i+1,role,frozenset({1})) for i,(name,role) in enumerate(zip(("informante","encuestador","supervisor","critico"),ROLES))}

    def login(self, usuario: str, password: str) -> str:
        candidate=hashlib.scrypt(password.encode(),salt=b"enph-public-demo",n=16384,r=8,p=1)
        if not hmac.compare_digest(candidate,self.password_hash) or usuario not in self.users:
            raise PermissionError("Credenciales demo inválidas")
        token=secrets.token_urlsafe(32)
        with self.lock:
            now=self.clock()
            self.sessions={t:v for t,v in self.sessions.items() if v[1]>now}
            self.sessions[token]=(self.users[usuario],now+1200)
        return token

    def resolve(self, token: str) -> Session:
        with self.lock:
            value=self.sessions.get(token)
            if not value or value[1]<=self.clock():
                self.sessions.pop(token,None)
                raise PermissionError("Sesión inválida o expirada")
            return value[0]
