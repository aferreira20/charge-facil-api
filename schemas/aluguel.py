"""Schemas de requisição e resposta das rotas de aluguel (totem)."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from model.aluguel import Aluguel


class AluguelSchema(BaseModel):
    """Dados enviados pelo totem para iniciar um aluguel. A API escolhe o power bank mais carregado."""
    estacao_id: int = Field(..., description="Estação de retirada", examples=[1])
    cliente_nome: str = Field(..., min_length=3, max_length=80, examples=["Maria Oliveira"])
    cliente_telefone: str = Field(..., min_length=8, max_length=20, examples=["(21) 99999-0000"])


class DevolucaoSchema(BaseModel):
    estacao_id: int = Field(..., description="Estação de devolução (pode ser qualquer uma)", examples=[2])


class AluguelPathSchema(BaseModel):
    aluguel_id: int = Field(..., description="ID do aluguel")


class AluguelBuscaSchema(BaseModel):
    situacao: Optional[Literal["ativo", "devolvido", "vendido"]] = Field(None, description="Filtra por situação")
    cliente: Optional[str] = Field(None, description="Busca parcial pelo nome ou telefone do cliente")


class AluguelViewSchema(BaseModel):
    id: int = Field(..., examples=[1])
    cliente_nome: str = Field(..., examples=["Maria Oliveira"])
    cliente_telefone: str = Field(..., examples=["(21) 99999-0000"])
    powerbank_codigo: str = Field(..., examples=["CF-0003"])
    situacao: str = Field(..., description="ativo, devolvido ou vendido", examples=["devolvido"])
    estacao_retirada: str = Field(..., examples=["Shopping Leblon"])
    estacao_devolucao: Optional[str] = Field(None, examples=["Metrô Carioca"])
    inicio: str = Field(..., examples=["2026-09-25T14:05:00"])
    prazo_devolucao: str = Field(..., description="Início + 24h. Depois disso vira venda", examples=["2026-09-26T14:05:00"])
    fim: Optional[str] = Field(None, examples=["2026-09-25T15:20:00"])
    duracao_minutos: int = Field(..., examples=[75])
    minutos_restantes: Optional[int] = Field(None, description="Minutos até o fim do prazo (só ativos)", examples=[1365])
    caucao: float = Field(..., description="Franquia pré-autorizada na retirada (R$)", examples=[150.0])
    valor: float = Field(..., description="Valor cobrado, ou uso acumulado se ativo (R$)", examples=[8.0])
    estorno: Optional[float] = Field(None, description="Diferença da franquia devolvida ao cliente (R$)", examples=[142.0])
    nivel_bateria: Optional[int] = Field(None, description="Carga atual do power bank (%)", examples=[64])


class ListaAlugueisSchema(BaseModel):
    alugueis: List[AluguelViewSchema]


def _iso(data):
    return data.isoformat(timespec="seconds") if data else None


def apresenta_aluguel(a: Aluguel) -> dict:
    return {
        "id": a.id,
        "cliente_nome": a.cliente_nome,
        "cliente_telefone": a.cliente_telefone,
        "powerbank_codigo": a.powerbank_codigo,
        "situacao": a.situacao,
        "estacao_retirada": a.retirada_nome,
        "estacao_devolucao": a.devolucao_nome,
        "inicio": _iso(a.inicio),
        "prazo_devolucao": _iso(a.prazo),
        "fim": _iso(a.fim),
        "duracao_minutos": a.duracao_minutos,
        "minutos_restantes": a.minutos_restantes,
        "caucao": a.caucao,
        "valor": a.valor_atual,
        "estorno": a.estorno,
        "nivel_bateria": a.powerbank.nivel_atual if a.powerbank else None,
    }


def apresenta_alugueis(alugueis: List[Aluguel]) -> dict:
    return {"alugueis": [apresenta_aluguel(a) for a in alugueis]}
