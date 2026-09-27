"""Dados de demonstração, carregados apenas quando o banco está vazio."""

from datetime import datetime, timedelta

from model.aluguel import Aluguel
from model.estacao import Estacao
from model.powerbank import PowerBank
from model.regras import ALUGADO, DEVOLVIDO, DISPONIVEL, MANUTENCAO, calcular_valor

ESTACOES = [
    # Formato: nome, endereço, bairro, cidade, capacidade, horário, qtd. de power banks
    ("Shopping Leblon", "Av. Afrânio de Melo Franco, 290 - Piso L1", "Leblon", "Rio de Janeiro", 12, "10h às 22h", 9),
    ("Aeroporto Santos Dumont", "Praça Senador Salgado Filho - Saguão B", "Centro", "Rio de Janeiro", 20, "24 horas", 14),
    ("Metrô Carioca", "Largo da Carioca - Mezanino", "Centro", "Rio de Janeiro", 12, "5h às 0h", 6),
    ("Parque Madureira", "Rua Soares Caldeira, 115 - Portão 2", "Madureira", "Rio de Janeiro", 8, "6h às 22h", 5),
    ("Plaza Niterói", "Rua XV de Novembro, 8 - Piso 1", "Centro", "Niterói", 12, "10h às 22h", 7),
    ("Rodoviária Novo Rio", "Av. Francisco Bicalho, 1 - Embarque", "Santo Cristo", "Rio de Janeiro", 16, "24 horas", 12),
]

CLIENTES = [
    ("Ana Souza", "(21) 99876-1122"), ("Bruno Lima", "(21) 98765-3344"),
    ("Carla Mendes", "(21) 97654-5566"), ("Diego Rocha", "(21) 96543-7788"),
    ("Elisa Martins", "(21) 95432-9900"), ("Felipe Costa", "(21) 94321-2233"),
    ("Gabriela Nunes", "(21) 93210-4455"), ("Henrique Alves", "(21) 92109-6677"),
]


def _retirar(pb, momento):
    """Retira o power bank da estação, como se um cliente o tivesse alugado."""
    origem = pb.estacao
    pb.mudar_status(ALUGADO, momento)
    pb.estacao = None
    return origem


def popular_dados_iniciais(session):
    if session.query(Estacao).count() > 0:
        return

    agora = datetime.now()
    estacoes, powerbanks = [], []
    seq = 1

    for i, (nome, end, bairro, cidade, cap, horario, qtd) in enumerate(ESTACOES):
        est = Estacao(nome, end, bairro, cidade, cap, horario, criada_em=agora - timedelta(days=60 - i * 7))
        session.add(est)
        session.flush()
        estacoes.append(est)
        for j in range(qtd):
            nivel = [100, 85, 64, 42, 18, 95, 73][(seq + j) % 7]
            pb = PowerBank(f"CF-{seq:04d}", [5000, 10000][seq % 2], est.id, nivel_bateria=nivel,
                           status=DISPONIVEL, nivel_atualizado_em=agora)
            if seq % 11 == 0:
                pb.status = MANUTENCAO
            session.add(pb)
            powerbanks.append(pb)
            seq += 1
    session.flush()

    # Unidades novas em estoque, aguardando alocação em uma estação
    for capacidade in [10000, 10000, 20000, 5000, 20000]:
        session.add(PowerBank(f"CF-{seq:04d}", capacidade))
        seq += 1
    session.flush()

    # Aluguéis devolvidos nos últimos dias (histórico, receita, estornos e ranking).
    # Os campos são preenchidos direto para os power banks de exemplo não mudarem de estação.
    livres = [pb for pb in powerbanks if pb.status != MANUTENCAO]
    duracoes = [35, 80, 150, 20, 4, 210, 95, 60, 125, 45, 300, 70]
    for k, minutos in enumerate(duracoes):
        pb = livres[k * 3 % len(livres)]
        origem = estacoes[k % len(estacoes)]
        destino = estacoes[(k * 2 + 1) % len(estacoes)]
        inicio = agora - timedelta(days=(k % 6), hours=3 + k)
        nome, tel = CLIENTES[k % len(CLIENTES)]
        aluguel = Aluguel(nome, tel, pb, origem, inicio=inicio)
        aluguel.situacao = DEVOLVIDO
        aluguel.fim = inicio + timedelta(minutes=minutos)
        aluguel.estacao_devolucao = destino
        aluguel.devolucao_nome = destino.nome
        aluguel.valor = calcular_valor(aluguel.inicio, aluguel.fim)
        aluguel.estorno = round(aluguel.caucao - aluguel.valor, 2)
        session.add(aluguel)

    # Aluguéis nunca devolvidos: a franquia foi retida e o power bank, vendido
    for k, dias in enumerate([3, 2]):
        pb = livres[-(k + 1)]
        inicio = agora - timedelta(days=dias, hours=5)
        origem = _retirar(pb, inicio)
        nome, tel = CLIENTES[6 + k]
        aluguel = Aluguel(nome, tel, pb, origem, inicio=inicio)
        session.add(aluguel)
        aluguel.converter_em_venda()

    # Aluguéis em andamento (o último está perto de atingir o prazo de 24h)
    for k, minutos in enumerate([42, 135, 23 * 60 + 5]):
        pb = livres[-(k + 3)]
        inicio = agora - timedelta(minutes=minutos)
        origem = _retirar(pb, inicio)
        nome, tel = CLIENTES[(k + 2) % len(CLIENTES)]
        session.add(Aluguel(nome, tel, pb, origem, inicio=inicio))

    session.commit()
