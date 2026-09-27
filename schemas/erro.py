"""Schema padrão de erro."""

from pydantic import BaseModel, Field


class ErroSchema(BaseModel):
    """Mensagem de erro retornada por todas as rotas."""
    mensagem: str = Field(..., examples=["Estação não encontrada"])
