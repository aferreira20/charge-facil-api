"""Reúne os schemas Pydantic usados nas rotas e na documentação OpenAPI."""

from schemas.erro import ErroSchema
from schemas.powerbank import (PowerBankSchema, PowerBankEstacaoSchema, PowerBankPathSchema, PowerBankBuscaSchema,
                               PowerBankStatusSchema, PowerBankViewSchema, ListaPowerBanksSchema,
                               PowerBankDelSchema, apresenta_powerbank, apresenta_powerbanks)
from schemas.estacao import (EstacaoSchema, EstacaoPathSchema, EstacaoBuscaSchema, EstacaoViewSchema,
                             EstacaoDetalheSchema, ListaEstacoesSchema, EstacaoDelSchema,
                             apresenta_estacao, apresenta_estacao_detalhe, apresenta_estacoes)
from schemas.aluguel import (AluguelSchema, DevolucaoSchema, AluguelPathSchema, AluguelBuscaSchema,
                             AluguelViewSchema, ListaAlugueisSchema, apresenta_aluguel, apresenta_alugueis)
from schemas.dashboard import DashboardSchema
