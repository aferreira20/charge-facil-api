"""Schemas de requisição e resposta das rotas de estações."""

from typing import List, Optional

from pydantic import BaseModel, Field

from model.estacao import Estacao
from schemas.powerbank import PowerBankViewSchema, apresenta_powerbank


class EstacaoSchema(BaseModel):
    """Dados para cadastrar ou atualizar uma estação."""
    nome: str = Field(..., min_length=3, max_length=80, examples=["Shopping Rio Sul"])
    endereco: str = Field(..., min_length=5, max_length=160, examples=["Rua Lauro Müller, 116 - Piso 2"])
    bairro: str = Field(..., min_length=2, max_length=60, examples=["Botafogo"])
    cidade: str = Field(..., min_length=2, max_length=60, examples=["Rio de Janeiro"])
    capacidade: int = Field(..., ge=4, le=40, description="Número de slots de power bank (4 a 40)", examples=[12])
    horario: str = Field("24 horas", max_length=40, examples=["10h às 22h"])
    ativa: bool = Field(True, description="Estação aceitando retiradas e devoluções")


class EstacaoPathSchema(BaseModel):
    estacao_id: int = Field(..., description="ID da estação")


class EstacaoBuscaSchema(BaseModel):
    """Filtros opcionais da listagem de estações."""
    busca: Optional[str] = Field(None, description="Filtra por nome, bairro ou cidade")
    apenas_ativas: bool = Field(False, description="Retorna só estações ativas")


class EstacaoViewSchema(BaseModel):
    id: int = Field(..., examples=[1])
    nome: str = Field(..., examples=["Shopping Leblon"])
    endereco: str = Field(..., examples=["Av. Afrânio de Melo Franco, 290 - Piso L1"])
    bairro: str = Field(..., examples=["Leblon"])
    cidade: str = Field(..., examples=["Rio de Janeiro"])
    capacidade: int = Field(..., examples=[12])
    horario: str = Field(..., examples=["10h às 22h"])
    ativa: bool = Field(..., examples=[True])
    criada_em: str = Field(..., examples=["2026-09-01T10:00:00"])
    slots_ocupados: int = Field(..., description="Power banks presentes na estação", examples=[9])
    slots_livres: int = Field(..., description="Slots livres para devolução", examples=[3])
    disponiveis: int = Field(..., description="Power banks prontos para aluguel (bateria >= 20%)", examples=[7])


class EstacaoDetalheSchema(EstacaoViewSchema):
    powerbanks: List[PowerBankViewSchema] = Field(..., description="Power banks presentes na estação")


class ListaEstacoesSchema(BaseModel):
    estacoes: List[EstacaoViewSchema]


class EstacaoDelSchema(BaseModel):
    mensagem: str = Field(..., examples=["Estação removida"])
    id: int = Field(..., examples=[1])


def apresenta_estacao(est: Estacao) -> dict:
    return {
        "id": est.id,
        "nome": est.nome,
        "endereco": est.endereco,
        "bairro": est.bairro,
        "cidade": est.cidade,
        "capacidade": est.capacidade,
        "horario": est.horario,
        "ativa": est.ativa,
        "criada_em": est.criada_em.isoformat(timespec="seconds"),
        "slots_ocupados": est.slots_ocupados,
        "slots_livres": est.slots_livres,
        "disponiveis": est.disponiveis,
    }


def apresenta_estacao_detalhe(est: Estacao) -> dict:
    dados = apresenta_estacao(est)
    dados["powerbanks"] = [apresenta_powerbank(pb) for pb in sorted(est.powerbanks, key=lambda p: p.codigo)]
    return dados


def apresenta_estacoes(estacoes: List[Estacao]) -> dict:
    return {"estacoes": [apresenta_estacao(e) for e in estacoes]}
