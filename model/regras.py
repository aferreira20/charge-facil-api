"""Regras de negócio compartilhadas pelos modelos: tarifa, franquia e simulação de bateria."""

import math
from datetime import datetime

# Status do power bank (em português, exatamente como a API expõe)
DISPONIVEL = "disponível"
ALUGADO = "alugado"
MANUTENCAO = "manutenção"
VENDIDO = "vendido"
ESTOQUE = "em estoque"   # cadastrado no inventário, ainda sem estação

# Situações do aluguel (a situação "vendido" reaproveita a constante VENDIDO)
ATIVO = "ativo"
DEVOLVIDO = "devolvido"

# Tabela de tarifas (em R$)
CARENCIA_MINUTOS = 5          # minutos iniciais gratuitos (carência)
TARIFA_PRIMEIRA_HORA = 5.00   # primeira hora iniciada
TARIFA_HORA_ADICIONAL = 3.00  # cada hora adicional iniciada
TETO_DIARIO = 25.00           # valor máximo de uso dentro da janela de 24h

# Franquia (caução): pré-autorizada na retirada; vira venda se não houver devolução no prazo
CAUCAO = 150.00
PRAZO_HORAS = 24

# Simulação de bateria (% por hora)
RECARGA_POR_HORA = 30         # enquanto está encaixado na estação
CONSUMO_POR_HORA = 20         # enquanto está alugado (carregando um celular)
NIVEL_MINIMO_ALUGUEL = 20     # abaixo disso o power bank não é liberado para aluguel


def minutos_entre(inicio: datetime, fim: datetime) -> int:
    """Retorna os minutos inteiros entre duas datas (nunca negativo)."""
    return max(0, int((fim - inicio).total_seconds() // 60))


def calcular_valor(inicio: datetime, fim: datetime) -> float:
    """Calcula o valor de uso: carência, cobrança por hora iniciada e limite de TETO_DIARIO."""
    minutos = minutos_entre(inicio, fim)
    if minutos <= CARENCIA_MINUTOS:
        return 0.0
    horas = math.ceil(minutos / 60)
    return round(min(TETO_DIARIO, TARIFA_PRIMEIRA_HORA + TARIFA_HORA_ADICIONAL * (horas - 1)), 2)


def nivel_projetado(nivel: int, desde: datetime, status: str, agora: datetime = None) -> int:
    """Projeta o nível de bateria atual a partir do último nível salvo e do tempo decorrido."""
    agora = agora or datetime.now()
    horas = max(0.0, (agora - desde).total_seconds() / 3600)
    if status == DISPONIVEL:
        return min(100, int(nivel + horas * RECARGA_POR_HORA))
    if status == ALUGADO:
        return max(0, int(nivel - horas * CONSUMO_POR_HORA))
    return nivel  # manutenção, estoque ou vendido: nível congelado
