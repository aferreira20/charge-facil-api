"""Modelo da tabela estacao."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from model.base import Base


class Estacao(Base):
    """Estação (totem) de recarga com um número fixo de slots para power banks."""

    __tablename__ = "estacao"

    id = Column(Integer, primary_key=True)
    nome = Column(String(80), unique=True, nullable=False)
    endereco = Column(String(160), nullable=False)
    bairro = Column(String(60), nullable=False)
    cidade = Column(String(60), nullable=False)
    capacidade = Column(Integer, nullable=False)
    horario = Column(String(40), nullable=False, default="24 horas")
    ativa = Column(Boolean, nullable=False, default=True)
    criada_em = Column(DateTime, nullable=False, default=datetime.now)

    powerbanks = relationship("PowerBank", back_populates="estacao")

    def __init__(self, nome, endereco, bairro, cidade, capacidade,
                 horario="24 horas", ativa=True, criada_em=None):
        self.nome = nome
        self.endereco = endereco
        self.bairro = bairro
        self.cidade = cidade
        self.capacidade = capacidade
        self.horario = horario
        self.ativa = ativa
        self.criada_em = criada_em or datetime.now()

    @property
    def slots_ocupados(self) -> int:
        """Slots em uso: todo power bank fisicamente encaixado na estação."""
        return len(self.powerbanks)

    @property
    def slots_livres(self) -> int:
        return max(0, self.capacidade - self.slots_ocupados)

    @property
    def disponiveis(self) -> int:
        """Power banks prontos para aluguel neste momento."""
        return sum(1 for pb in self.powerbanks if pb.pronto_para_aluguel)
