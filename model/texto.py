"""Utilitários de texto usados nas buscas."""

import unicodedata


def normalizar(texto) -> str:
    """Remove acentos e converte para minúsculas, para buscas como "niteroi" acharem "Niterói"."""
    if texto is None:
        return ""
    decomposto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()
