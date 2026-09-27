"""Schemas de resposta do dashboard."""

from typing import List

from pydantic import BaseModel, Field


class RankingEstacaoSchema(BaseModel):
    estacao: str = Field(..., examples=["Aeroporto Santos Dumont"])
    retiradas: int = Field(..., examples=[12])


class TarifaSchema(BaseModel):
    carencia_minutos: int = Field(..., examples=[5])
    primeira_hora: float = Field(..., examples=[5.0])
    hora_adicional: float = Field(..., examples=[3.0])
    teto_diario: float = Field(..., examples=[25.0])
    caucao: float = Field(..., description="Franquia pré-autorizada na retirada", examples=[150.0])
    prazo_horas: int = Field(..., description="Prazo para devolver antes de virar venda", examples=[24])


class DashboardSchema(BaseModel):
    """Indicadores consolidados da rede."""
    estacoes_total: int = Field(..., examples=[6])
    estacoes_ativas: int = Field(..., examples=[6])
    powerbanks_total: int = Field(..., description="Inventário ativo: estações, estoque e alugados (exclui vendidos)", examples=[56])
    powerbanks_disponiveis: int = Field(..., description="Prontos para aluguel", examples=[40])
    powerbanks_alugados: int = Field(..., examples=[3])
    powerbanks_manutencao: int = Field(..., examples=[4])
    powerbanks_estoque: int = Field(..., description="Cadastrados e ainda não alocados em estação", examples=[5])
    powerbanks_vendidos: int = Field(..., description="Não devolvidos em 24h", examples=[2])
    alugueis_ativos: int = Field(..., examples=[3])
    alugueis_vencendo: int = Field(..., description="Ativos com menos de 2h para o fim do prazo", examples=[1])
    alugueis_hoje: int = Field(..., description="Retiradas iniciadas hoje", examples=[5])
    receita_hoje: float = Field(..., description="Uso + vendas encerrados hoje (R$)", examples=[32.0])
    receita_uso: float = Field(..., description="Total cobrado por uso (R$)", examples=[97.0])
    receita_vendas: float = Field(..., description="Total de franquias retidas (R$)", examples=[300.0])
    estornos_total: float = Field(..., description="Total devolvido aos clientes (R$)", examples=[1703.0])
    duracao_media_minutos: int = Field(..., description="Média dos aluguéis devolvidos", examples=[98])
    ocupacao_rede: int = Field(..., description="Percentual de slots ocupados na rede", examples=[62])
    ranking_estacoes: List[RankingEstacaoSchema] = Field(..., description="Top 5 estações por retiradas")
    tarifa: TarifaSchema
