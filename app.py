"""API da rede Charge Fácil: rotas REST documentadas com OpenAPI (Swagger)."""

from datetime import datetime

from flask import redirect
from flask_cors import CORS
from flask_openapi3 import Info, OpenAPI, Tag
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from model import Aluguel, Estacao, PowerBank, Session, converter_alugueis_vencidos, normalizar
from model.regras import (ALUGADO, ATIVO, CARENCIA_MINUTOS, CAUCAO, DEVOLVIDO, DISPONIVEL, ESTOQUE, MANUTENCAO,
                          PRAZO_HORAS, TARIFA_HORA_ADICIONAL, TARIFA_PRIMEIRA_HORA, TETO_DIARIO,
                          VENDIDO)
from schemas import *

info = Info(
    title="Charge Fácil API",
    version="2.0.0",
    description="API da rede Charge Fácil de estações de aluguel de power banks: retire em uma "
                "estação e devolva em qualquer outra em até 24h. Na retirada é pré-autorizada uma "
                "franquia de R$ 150,00: na devolução cobra-se só o uso e a diferença é estornada; "
                "sem devolução no prazo, a franquia é cobrada e o power bank passa a ser do cliente.",
)
app = OpenAPI(__name__, info=info)
# O front-end é aberto direto do disco (file://), por isso todas as origens são liberadas
CORS(app)

estacao_tag = Tag(name="Estações", description="Cadastro e consulta das estações (totens) da rede")
powerbank_tag = Tag(name="Inventário", description="Power banks em estoque, alocados em estações, alugados e vendidos")
aluguel_tag = Tag(name="Aluguéis (totem)", description="Retirada e devolução feitas no autoatendimento do totem")
dashboard_tag = Tag(name="Dashboard", description="Indicadores consolidados da rede")


def erro(mensagem: str, status: int):
    return {"mensagem": mensagem}, status


@app.get("/", doc_ui=False)
def home():
    """Redireciona para a documentação Swagger."""
    return redirect("/openapi/swagger")


# ---------------------------------------------------------------- Estações

@app.get("/estacoes", tags=[estacao_tag],
         responses={200: ListaEstacoesSchema})
def listar_estacoes(query: EstacaoBuscaSchema):
    """Lista as estações, com busca opcional por nome, bairro ou cidade.

    Retorna a ocupação de cada estação: slots ocupados, slots livres e power banks prontos para aluguel.
    """
    with Session() as session:
        converter_alugueis_vencidos(session)
        consulta = session.query(Estacao)
        if query.busca:
            # Busca sem diferenciar acentos nem maiúsculas: "niteroi" encontra "Niterói"
            termo = f"%{normalizar(query.busca.strip())}%"
            consulta = consulta.filter(or_(func.sem_acento(Estacao.nome).like(termo),
                                           func.sem_acento(Estacao.bairro).like(termo),
                                           func.sem_acento(Estacao.cidade).like(termo)))
        if query.apenas_ativas:
            consulta = consulta.filter(Estacao.ativa.is_(True))
        return apresenta_estacoes(consulta.order_by(Estacao.nome).all()), 200


@app.get("/estacoes/<int:estacao_id>", tags=[estacao_tag],
         responses={200: EstacaoDetalheSchema, 404: ErroSchema})
def buscar_estacao(path: EstacaoPathSchema):
    """Busca uma estação pelo ID, incluindo os power banks presentes nela."""
    with Session() as session:
        estacao = session.get(Estacao, path.estacao_id)
        if not estacao:
            return erro("Estação não encontrada", 404)
        return apresenta_estacao_detalhe(estacao), 200


@app.post("/estacoes", tags=[estacao_tag],
          responses={201: EstacaoViewSchema, 409: ErroSchema})
def cadastrar_estacao(body: EstacaoSchema):
    """Cadastra uma nova estação. O nome deve ser único."""
    with Session() as session:
        estacao = Estacao(**body.model_dump())
        try:
            session.add(estacao)
            session.commit()
        except IntegrityError:
            session.rollback()
            return erro("Já existe uma estação com esse nome", 409)
        return apresenta_estacao(estacao), 201


@app.put("/estacoes/<int:estacao_id>", tags=[estacao_tag],
         responses={200: EstacaoViewSchema, 404: ErroSchema, 409: ErroSchema})
def atualizar_estacao(path: EstacaoPathSchema, body: EstacaoSchema):
    """Atualiza todos os dados de uma estação.

    A capacidade não pode ficar menor que o número de power banks presentes nela.
    """
    with Session() as session:
        estacao = session.get(Estacao, path.estacao_id)
        if not estacao:
            return erro("Estação não encontrada", 404)
        if body.capacidade < estacao.slots_ocupados:
            return erro(f"A estação tem {estacao.slots_ocupados} power banks; "
                        f"a capacidade não pode ser menor que isso", 409)
        for campo, valor in body.model_dump().items():
            setattr(estacao, campo, valor)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return erro("Já existe uma estação com esse nome", 409)
        return apresenta_estacao(estacao), 200


@app.delete("/estacoes/<int:estacao_id>", tags=[estacao_tag],
            responses={200: EstacaoDelSchema, 404: ErroSchema, 409: ErroSchema})
def remover_estacao(path: EstacaoPathSchema):
    """Remove uma estação vazia (sem power banks).

    O histórico de aluguéis é preservado.
    """
    with Session() as session:
        estacao = session.get(Estacao, path.estacao_id)
        if not estacao:
            return erro("Estação não encontrada", 404)
        if estacao.slots_ocupados > 0:
            return erro("Retire ou remova os power banks da estação antes de excluí-la", 409)
        session.delete(estacao)
        session.commit()
        return {"mensagem": "Estação removida", "id": path.estacao_id}, 200


# ---------------------------------------------------------------- Inventário (power banks)

@app.get("/powerbanks", tags=[powerbank_tag],
         responses={200: ListaPowerBanksSchema})
def listar_powerbanks(query: PowerBankBuscaSchema):
    """Consulta o inventário de power banks, com filtros por estação, status e busca.

    Sem filtro de status, retorna só a frota em operação. Com `status=vendido`, retorna os power banks
    não devolvidos em 24h, com os dados da venda (comprador, data e valor), e a `busca` também
    procura pelo nome ou telefone do comprador.
    O nível de bateria é simulado: recarrega 30%/h na estação e descarrega 20%/h em uso.
    """
    with Session() as session:
        converter_alugueis_vencidos(session)
        consulta = session.query(PowerBank)
        if query.status:
            consulta = consulta.filter(PowerBank.status == query.status)
        else:
            consulta = consulta.filter(PowerBank.status != VENDIDO)
        if query.estacao_id is not None:
            consulta = consulta.filter(PowerBank.estacao_id == query.estacao_id)
        powerbanks = consulta.order_by(PowerBank.codigo).all()

        if query.busca:
            termo = normalizar(query.busca.strip())

            def corresponde(pb):
                venda = pb.venda
                campos = [pb.codigo]
                if venda:
                    campos += [venda.cliente_nome, venda.cliente_telefone]
                return any(termo in normalizar(c) for c in campos)

            powerbanks = [pb for pb in powerbanks if corresponde(pb)]
        return apresenta_powerbanks(powerbanks), 200


@app.post("/powerbanks", tags=[powerbank_tag],
          responses={201: PowerBankViewSchema})
def adicionar_powerbank(body: PowerBankSchema):
    """Cadastra um power bank novo no inventário, com status "em estoque" e 100% de carga.

    O código (CF-0001, CF-0002...) é gerado automaticamente. Para colocá-lo em uso,
    aloque-o em uma estação com `PATCH /powerbanks/{id}/estacao`.
    """
    with Session() as session:
        proximo = (session.query(func.max(PowerBank.id)).scalar() or 0) + 1
        while session.query(PowerBank).filter_by(codigo=f"CF-{proximo:04d}").first():
            proximo += 1
        powerbank = PowerBank(f"CF-{proximo:04d}", body.capacidade_mah)
        session.add(powerbank)
        session.commit()
        return apresenta_powerbank(powerbank), 201


@app.patch("/powerbanks/<int:powerbank_id>/estacao", tags=[powerbank_tag],
           responses={200: PowerBankViewSchema, 404: ErroSchema, 409: ErroSchema})
def alocar_powerbank(path: PowerBankPathSchema, body: PowerBankEstacaoSchema):
    """Aloca um power bank do estoque em uma estação, ou o recolhe de volta ao estoque.

    - Com `estacao_id`: o power bank precisa estar em estoque e a estação precisa ter slot livre.
      Ele passa a "disponível" e começa a recarregar.
    - Com `estacao_id` nulo: o power bank sai da estação (liberando o slot) e volta a "em estoque".
      Não vale para power banks alugados ou vendidos.
    """
    with Session() as session:
        powerbank = session.get(PowerBank, path.powerbank_id)
        if not powerbank:
            return erro("Power bank não encontrado", 404)

        if body.estacao_id is None:
            if powerbank.status == ESTOQUE:
                return erro("O power bank já está em estoque", 409)
            if powerbank.status in (ALUGADO, VENDIDO):
                return erro(f"Um power bank {powerbank.status} não pode ser recolhido ao estoque", 409)
            powerbank.mudar_status(ESTOQUE)
            powerbank.estacao = None
        else:
            if powerbank.status != ESTOQUE:
                return erro("Só power banks em estoque podem ser alocados; recolha-o ao estoque primeiro", 409)
            estacao = session.get(Estacao, body.estacao_id)
            if not estacao:
                return erro("Estação não encontrada", 404)
            if estacao.slots_livres == 0:
                return erro("A estação está lotada: não há slot livre", 409)
            powerbank.mudar_status(DISPONIVEL)
            powerbank.estacao = estacao
        session.commit()
        return apresenta_powerbank(powerbank), 200


@app.patch("/powerbanks/<int:powerbank_id>/status", tags=[powerbank_tag],
           responses={200: PowerBankViewSchema, 404: ErroSchema, 409: ErroSchema})
def alterar_status_powerbank(path: PowerBankPathSchema, body: PowerBankStatusSchema):
    """Coloca um power bank em manutenção ou o libera para uso.

    Vale só para power banks alocados em estação (não para em estoque, alugados ou vendidos).
    """
    with Session() as session:
        powerbank = session.get(PowerBank, path.powerbank_id)
        if not powerbank:
            return erro("Power bank não encontrado", 404)
        if powerbank.status == ALUGADO:
            return erro("O power bank está alugado; aguarde a devolução", 409)
        if powerbank.status == VENDIDO:
            return erro("O power bank foi vendido e não faz mais parte da frota", 409)
        if powerbank.status == ESTOQUE:
            return erro("O power bank está em estoque; aloque-o em uma estação primeiro", 409)
        powerbank.mudar_status(body.status)
        session.commit()
        return apresenta_powerbank(powerbank), 200


@app.delete("/powerbanks/<int:powerbank_id>", tags=[powerbank_tag],
            responses={200: PowerBankDelSchema, 404: ErroSchema, 409: ErroSchema})
def remover_powerbank(path: PowerBankPathSchema):
    """Descarta um power bank da frota.

    Não é permitido remover um power bank alugado nem um vendido (o registro da venda é mantido).
    """
    with Session() as session:
        powerbank = session.get(PowerBank, path.powerbank_id)
        if not powerbank:
            return erro("Power bank não encontrado", 404)
        if powerbank.status == ALUGADO:
            return erro("O power bank está alugado; aguarde a devolução", 409)
        if powerbank.status == VENDIDO:
            return erro("Power banks vendidos ficam no inventário como registro da venda", 409)
        codigo = powerbank.codigo
        session.delete(powerbank)
        session.commit()
        return {"mensagem": "Power bank removido", "codigo": codigo}, 200


# ---------------------------------------------------------------- Aluguéis (totem)

@app.get("/alugueis", tags=[aluguel_tag],
         responses={200: ListaAlugueisSchema})
def listar_alugueis(query: AluguelBuscaSchema):
    """Lista os aluguéis (mais recentes primeiro), com filtro por situação e cliente.

    Usada pelo totem para localizar o aluguel do cliente pelo telefone na hora da devolução.
    Aluguéis ativos trazem o uso acumulado e os minutos que faltam para o prazo de 24h.
    """
    with Session() as session:
        converter_alugueis_vencidos(session)
        consulta = session.query(Aluguel)
        if query.situacao:
            consulta = consulta.filter(Aluguel.situacao == query.situacao)
        if query.cliente:
            termo = query.cliente.strip()
            digitos = "".join(c for c in termo if c.isdigit())
            filtros = [func.sem_acento(Aluguel.cliente_nome).like(f"%{normalizar(termo)}%"),
                       Aluguel.cliente_telefone.like(f"%{termo}%")]
            if len(digitos) >= 4:
                # Compara só os dígitos, para "(21) 99999-0000" e "21999990000" serem o mesmo telefone
                telefone = func.replace(func.replace(func.replace(func.replace(
                    Aluguel.cliente_telefone, "(", ""), ")", ""), "-", ""), " ", "")
                filtros.append(telefone.like(f"%{digitos}%"))
            consulta = consulta.filter(or_(*filtros))
        return apresenta_alugueis(consulta.order_by(Aluguel.inicio.desc()).all()), 200


@app.post("/alugueis", tags=[aluguel_tag],
          responses={201: AluguelViewSchema, 404: ErroSchema, 409: ErroSchema})
def iniciar_aluguel(body: AluguelSchema):
    """Inicia um aluguel no totem: pré-autoriza a franquia de R$ 150,00 e libera o power bank mais carregado.

    Só são liberados power banks disponíveis com pelo menos 20% de bateria. O prazo de devolução é de 24h.
    """
    with Session() as session:
        estacao = session.get(Estacao, body.estacao_id)
        if not estacao:
            return erro("Estação não encontrada", 404)
        if not estacao.ativa:
            return erro("Estação inativa no momento", 409)

        candidatos = [pb for pb in estacao.powerbanks if pb.pronto_para_aluguel]
        if not candidatos:
            return erro("Nenhum power bank com carga suficiente nesta estação", 409)
        powerbank = max(candidatos, key=lambda pb: pb.nivel_atual)

        agora = datetime.now()
        aluguel = Aluguel(body.cliente_nome.strip(), body.cliente_telefone.strip(), powerbank, estacao, agora)
        powerbank.mudar_status(ALUGADO, agora)
        powerbank.estacao = None
        session.add(aluguel)
        session.commit()
        return apresenta_aluguel(aluguel), 201


@app.patch("/alugueis/<int:aluguel_id>/devolucao", tags=[aluguel_tag],
           responses={200: AluguelViewSchema, 404: ErroSchema, 409: ErroSchema})
def devolver_powerbank(path: AluguelPathSchema, body: DevolucaoSchema):
    """Devolve o power bank no totem de qualquer estação ativa com slot livre, dentro do prazo de 24h.

    Cobra só o uso (5 min de carência, R$ 5,00 a primeira hora, R$ 3,00 por hora adicional, máximo de
    R$ 25,00) e estorna o restante da franquia. Após 24h o aluguel já foi convertido em venda (409).
    """
    with Session() as session:
        converter_alugueis_vencidos(session)
        aluguel = session.get(Aluguel, path.aluguel_id)
        if not aluguel:
            return erro("Aluguel não encontrado", 404)
        if aluguel.situacao == VENDIDO:
            return erro(f"Prazo de {PRAZO_HORAS}h expirado: a franquia foi cobrada e o power bank "
                        f"agora pertence ao cliente", 409)
        if aluguel.situacao == DEVOLVIDO:
            return erro("Este aluguel já foi finalizado", 409)
        estacao = session.get(Estacao, body.estacao_id)
        if not estacao:
            return erro("Estação não encontrada", 404)
        if not estacao.ativa:
            return erro("Estação inativa no momento", 409)
        if estacao.slots_livres == 0:
            return erro("Estação lotada: escolha outra estação para devolver", 409)

        aluguel.finalizar(estacao)
        session.commit()
        return apresenta_aluguel(aluguel), 200


# ---------------------------------------------------------------- Dashboard

@app.get("/dashboard", tags=[dashboard_tag],
         responses={200: DashboardSchema})
def dashboard():
    """Indicadores da rede: frota, ocupação, aluguéis, receita, estornos, vendas e ranking de estações."""
    with Session() as session:
        converter_alugueis_vencidos(session)
        estacoes = session.query(Estacao).all()
        powerbanks = session.query(PowerBank).all()
        alugueis = session.query(Aluguel).all()

        hoje = datetime.now().date()
        em_operacao = [pb for pb in powerbanks if pb.status != VENDIDO]
        ativos = [a for a in alugueis if a.situacao == ATIVO]
        devolvidos = [a for a in alugueis if a.situacao == DEVOLVIDO]
        vendidos = [a for a in alugueis if a.situacao == VENDIDO]
        encerrados = devolvidos + vendidos
        capacidade_total = sum(e.capacidade for e in estacoes) or 1
        presentes = sum(e.slots_ocupados for e in estacoes)

        retiradas = {}
        for a in alugueis:
            retiradas[a.retirada_nome] = retiradas.get(a.retirada_nome, 0) + 1
        ranking = sorted(retiradas.items(), key=lambda item: item[1], reverse=True)[:5]

        return {
            "estacoes_total": len(estacoes),
            "estacoes_ativas": sum(1 for e in estacoes if e.ativa),
            "powerbanks_total": len(em_operacao),
            "powerbanks_disponiveis": sum(1 for pb in em_operacao if pb.pronto_para_aluguel),
            "powerbanks_alugados": sum(1 for pb in em_operacao if pb.status == ALUGADO),
            "powerbanks_manutencao": sum(1 for pb in em_operacao if pb.status == MANUTENCAO),
            "powerbanks_estoque": sum(1 for pb in em_operacao if pb.status == ESTOQUE),
            "powerbanks_vendidos": len(powerbanks) - len(em_operacao),
            "alugueis_ativos": len(ativos),
            "alugueis_vencendo": sum(1 for a in ativos if a.minutos_restantes < 120),
            "alugueis_hoje": sum(1 for a in alugueis if a.inicio.date() == hoje),
            "receita_hoje": round(sum(a.valor for a in encerrados if a.fim.date() == hoje), 2),
            "receita_uso": round(sum(a.valor for a in devolvidos), 2),
            "receita_vendas": round(sum(a.valor for a in vendidos), 2),
            "estornos_total": round(sum(a.estorno for a in devolvidos), 2),
            "duracao_media_minutos": (sum(a.duracao_minutos for a in devolvidos) // len(devolvidos)
                                      if devolvidos else 0),
            "ocupacao_rede": round(presentes * 100 / capacidade_total),
            "ranking_estacoes": [{"estacao": nome, "retiradas": qtd} for nome, qtd in ranking],
            "tarifa": {
                "carencia_minutos": CARENCIA_MINUTOS,
                "primeira_hora": TARIFA_PRIMEIRA_HORA,
                "hora_adicional": TARIFA_HORA_ADICIONAL,
                "teto_diario": TETO_DIARIO,
                "caucao": CAUCAO,
                "prazo_horas": PRAZO_HORAS,
            },
        }, 200


if __name__ == "__main__":
    app.run(debug=True)
