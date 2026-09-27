"""Schemas de requisição e resposta das rotas de inventário (power banks)."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from model.powerbank import PowerBank


class PowerBankSchema(BaseModel):
    """Dados para cadastrar um power bank no estoque. O código (CF-0001...) é gerado pela API."""
    capacidade_mah: Literal[5000, 10000, 20000] = Field(10000, description="Capacidade em mAh")


class PowerBankEstacaoSchema(BaseModel):
    """Aloca um power bank do estoque em uma estação ou o recolhe de volta ao estoque."""
    estacao_id: Optional[int] = Field(
        None, description="Estação de destino. Vazio (null) recolhe o power bank ao estoque", examples=[1])


class PowerBankPathSchema(BaseModel):
    powerbank_id: int = Field(..., description="ID do power bank")


class PowerBankBuscaSchema(BaseModel):
    """Filtros opcionais da consulta ao inventário."""
    estacao_id: Optional[int] = Field(None, description="Só power banks desta estação")
    status: Optional[Literal["em estoque", "disponível", "alugado", "manutenção", "vendido"]] = Field(
        None, description="Filtra por status. Sem filtro, retorna só a frota em operação (exclui vendidos)")
    busca: Optional[str] = Field(None, description="Código do power bank ou, para vendidos, nome/telefone do comprador")


class PowerBankStatusSchema(BaseModel):
    status: Literal["disponível", "manutenção"] = Field(
        ..., description="Coloca em manutenção ou libera para uso. Vale só para power banks alocados em estação")


class VendaSchema(BaseModel):
    """Dados da venda de um power bank não devolvido em 24h."""
    aluguel_id: int = Field(..., examples=[14])
    cliente_nome: str = Field(..., examples=["Gabriela Nunes"])
    cliente_telefone: str = Field(..., examples=["(21) 93210-4455"])
    estacao_retirada: str = Field(..., examples=["Rodoviária Novo Rio"])
    retirado_em: str = Field(..., examples=["2026-09-22T18:00:00"])
    vendido_em: str = Field(..., description="Fim do prazo de 24h", examples=["2026-09-23T18:00:00"])
    valor: float = Field(..., description="Valor da franquia cobrado (R$)", examples=[150.0])


class PowerBankViewSchema(BaseModel):
    id: int = Field(..., examples=[1])
    codigo: str = Field(..., examples=["CF-0001"])
    capacidade_mah: int = Field(..., examples=[10000])
    status: str = Field(..., examples=["disponível"])
    nivel_bateria: int = Field(..., description="Nível atual simulado (%)", examples=[87])
    pronto_para_aluguel: bool = Field(..., examples=[True])
    estacao_id: Optional[int] = Field(None, description="Nulo quando em estoque, alugado ou vendido", examples=[1])
    estacao_nome: Optional[str] = Field(None, examples=["Shopping Leblon"])
    venda: Optional[VendaSchema] = Field(None, description="Preenchido apenas para power banks vendidos")


class ListaPowerBanksSchema(BaseModel):
    powerbanks: List[PowerBankViewSchema]


class PowerBankDelSchema(BaseModel):
    mensagem: str = Field(..., examples=["Power bank removido"])
    codigo: str = Field(..., examples=["CF-0001"])


def apresenta_venda(pb: PowerBank):
    venda = pb.venda
    if not venda:
        return None
    return {
        "aluguel_id": venda.id,
        "cliente_nome": venda.cliente_nome,
        "cliente_telefone": venda.cliente_telefone,
        "estacao_retirada": venda.retirada_nome,
        "retirado_em": venda.inicio.isoformat(timespec="seconds"),
        "vendido_em": venda.fim.isoformat(timespec="seconds"),
        "valor": venda.valor,
    }


def apresenta_powerbank(pb: PowerBank) -> dict:
    return {
        "id": pb.id,
        "codigo": pb.codigo,
        "capacidade_mah": pb.capacidade_mah,
        "status": pb.status,
        "nivel_bateria": pb.nivel_atual,
        "pronto_para_aluguel": pb.pronto_para_aluguel,
        "estacao_id": pb.estacao_id,
        "estacao_nome": pb.estacao.nome if pb.estacao else None,
        "venda": apresenta_venda(pb),
    }


def apresenta_powerbanks(pbs: List[PowerBank]) -> dict:
    return {"powerbanks": [apresenta_powerbank(pb) for pb in pbs]}
