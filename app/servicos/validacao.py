import re
import unicodedata

# Validação propositalmente simples: evita dependências fora da stack.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SENHA_MINIMA = 8


def email_valido(email: str) -> bool:
    return bool(_EMAIL.match(email or ""))


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def sem_acentos(texto: str) -> str:
    """Remove acentos e converte ª/º em a/o (ex.: "35ª Ação" -> "35a Acao")."""
    decomposto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def slug(texto: str, padrao: str = "item") -> str:
    """Trecho seguro para nome de arquivo (ex.: "35ª META 2026" -> "35a-meta-2026")."""
    return re.sub(r"[^a-z0-9]+", "-", sem_acentos(texto).lower()).strip("-") or padrao
