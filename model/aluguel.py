"""Modelo da tabela aluguel e rotina de conversão de aluguéis vencidos em venda."""

from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from model.base import Base
from model.regras import (ATIVO, CAUCAO, DEVOLVIDO, DISPONIVEL, PRAZO_HORAS, VENDIDO,
                          calcular_valor, minutos_entre)


class Aluguel(Base):
    """Aluguel: retirada em uma estação e devolução em qualquer estação em até 24h.

    Na retirada é pré-autorizada uma franquia de R$ 150,00. Na devolução, cobra-se
    apenas o uso e a diferença é estornada. Se o prazo vencer, a franquia é retida
    e o power bank passa a pertencer ao cliente.
    """

    __tablename__ = "aluguel"

    id = Column(Integer, primary_key=True)
    cliente_nome = Column(String(80), nullable=False)
    cliente_telefone = Column(String(20), nullable=False)
    powerbank_id = Column(Integer, ForeignKey("powerbank.id", ondelete="SET NULL"), nullable=True)
    estacao_retirada_id = Column(Integer, ForeignKey("estacao.id", ondelete="SET NULL"), nullable=True)
    estacao_devolucao_id = Column(Integer, ForeignKey("estacao.id", ondelete="SET NULL"), nullable=True)
    situacao = Column(String(20), nullable=False, default=ATIVO)
    inicio = Column(DateTime, nullable=False, default=datetime.now)
    prazo = Column(DateTime, nullable=False)
    fim = Column(DateTime, nullable=True)
    caucao = Column(Float, nullable=False, default=CAUCAO)
    valor = Column(Float, nullable=True)     # valor efetivamente cobrado
    estorno = Column(Float, nullable=True)   # parte da franquia devolvida ao cliente
    # Cópias dos nomes mantêm o histórico legível mesmo se a estação ou o power bank forem excluídos
    powerbank_codigo = Column(String(20), nullable=False)
    retirada_nome = Column(String(80), nullable=False)
    devolucao_nome = Column(String(80), nullable=True)

    powerbank = relationship("PowerBank", back_populates="alugueis")
    estacao_retirada = relationship("Estacao", foreign_keys=[estacao_retirada_id])
    estacao_devolucao = relationship("Estacao", foreign_keys=[estacao_devolucao_id])

    def __init__(self, cliente_nome, cliente_telefone, powerbank, estacao_retirada, inicio=None):
        self.cliente_nome = cliente_nome
        self.cliente_telefone = cliente_telefone
        self.powerbank = powerbank
        self.powerbank_codigo = powerbank.codigo
        self.estacao_retirada = estacao_retirada
        self.retirada_nome = estacao_retirada.nome
        self.inicio = inicio or datetime.now()
        self.prazo = self.inicio + timedelta(hours=PRAZO_HORAS)
        self.situacao = ATIVO
        self.caucao = CAUCAO

    @property
    def ativo(self) -> bool:
        return self.situacao == ATIVO

    @property
    def duracao_minutos(self) -> int:
        return minutos_entre(self.inicio, self.fim or datetime.now())

    @property
    def minutos_restantes(self):
        """Minutos restantes até a franquia virar venda (apenas para aluguel ativo)."""
        if not self.ativo:
            return None
        return minutos_entre(datetime.now(), self.prazo)

    @property
    def valor_atual(self) -> float:
        """Valor final se encerrado; caso contrário, o uso acumulado até agora."""
        if self.valor is not None:
            return self.valor
        return calcular_valor(self.inicio, datetime.now())

    def finalizar(self, estacao_devolucao, momento: datetime = None):
        """Devolução no prazo: cobra só o uso e estorna o restante da franquia."""
        self.fim = momento or datetime.now()
        self.situacao = DEVOLVIDO
        self.estacao_devolucao = estacao_devolucao
        self.devolucao_nome = estacao_devolucao.nome
        self.valor = calcular_valor(self.inicio, self.fim)
        self.estorno = round(self.caucao - self.valor, 2)
        if self.powerbank:
            self.powerbank.mudar_status(DISPONIVEL, self.fim)
            self.powerbank.estacao = estacao_devolucao

    def converter_em_venda(self):
        """Prazo vencido: retém a franquia inteira e marca o power bank como vendido."""
        self.fim = self.prazo
        self.situacao = VENDIDO
        self.valor = self.caucao
        self.estorno = 0.0
        if self.powerbank:
            self.powerbank.mudar_status(VENDIDO, self.prazo)
            self.powerbank.estacao = None


def converter_alugueis_vencidos(session, agora: datetime = None) -> int:
    """Converte em venda todo aluguel ativo com prazo vencido e retorna quantos foram convertidos."""
    agora = agora or datetime.now()
    vencidos = session.query(Aluguel).filter(Aluguel.situacao == ATIVO, Aluguel.prazo <= agora).all()
    for aluguel in vencidos:
        aluguel.converter_em_venda()
    if vencidos:
        session.commit()
    return len(vencidos)
