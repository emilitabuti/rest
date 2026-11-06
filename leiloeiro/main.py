"""Leiloeiro: o servidor REST do leilão (feito com FastAPI)."""
import argparse
import json
import os
import threading
from datetime import datetime, timedelta, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Leilão REST - Leiloeiro")

# Por enquanto só existe um leilão, então o id dele é sempre 1
LEILAO_ID = 1

# Várias requisições podem chegar ao mesmo tempo (cada uma roda numa thread).
# O lock faz uma de cada vez mexer nos lances, pra dois lances não se atropelarem.
_lock = threading.Lock()

# Dados do leilão (item, lance mínimo, horário de fim). São preenchidos no main().
_leilao: dict = {}

# Lista com todos os lances aceitos. O último da lista é sempre o maior.
# Por padrão os dados ficam só na memória: se o servidor cair, tudo se perde.
_lances: list[dict] = []

# Se for informado, é o arquivo JSON onde o estado é salvo (veja --arquivo no main()).
_arquivo: str | None = None


def _salvar() -> None:
    """Grava o leilão e os lances no arquivo (só se o --arquivo foi usado)."""
    if not _arquivo:
        return
    dados = {
        "item": _leilao["item"],
        "lance_minimo": _leilao["lance_minimo"],
        "encerra_em": _leilao["encerra_em"].isoformat(),
        "lances": _lances,
    }
    # Escreve num arquivo temporário e troca depois, pra não corromper se cair no meio
    with open(_arquivo + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dados, f)
    os.replace(_arquivo + ".tmp", _arquivo)


def _carregar() -> bool:
    """Lê o estado salvo. Devolve False se não existe arquivo ainda."""
    if not _arquivo or not os.path.exists(_arquivo):
        return False
    with open(_arquivo, encoding="utf-8") as f:
        dados = json.load(f)
    _leilao.update(
        item=dados["item"],
        lance_minimo=dados["lance_minimo"],
        encerra_em=datetime.fromisoformat(dados["encerra_em"]),
    )
    _lances.extend(dados["lances"])
    return True


class LanceIn(BaseModel):
    """Formato do JSON que o participante manda quando dá um lance."""

    participante: str = Field(min_length=1)  # nome não pode ser vazio
    valor: float = Field(gt=0)  # valor tem que ser maior que zero


def _agora() -> datetime:
    # Sempre usamos o relógio do servidor (em UTC) pra decidir tudo
    return datetime.now(timezone.utc)


def _encerrado() -> bool:
    # Não tem timer: só comparamos a hora atual com a hora de encerramento
    return _agora() >= _leilao["encerra_em"]


def _estado() -> dict:
    """Monta o JSON com a situação atual do leilão."""
    encerrado = _encerrado()
    maior = _lances[-1] if _lances else None  # None = ainda ninguém deu lance
    restante = max(0.0, (_leilao["encerra_em"] - _agora()).total_seconds())
    return {
        "id": LEILAO_ID,
        "item": _leilao["item"],
        "lance_minimo": _leilao["lance_minimo"],
        "maior_lance": maior,
        "encerra_em": _leilao["encerra_em"].isoformat(),
        "tempo_restante_s": round(restante, 1),
        "status": "ENCERRADO" if encerrado else "ABERTO",
        # O vencedor só aparece depois que o leilão acaba
        "vencedor": (maior["participante"] if maior else None) if encerrado else None,
    }


def _checar_id(leilao_id: int) -> None:
    # Se pedirem um leilão que não existe, responde 404 (não encontrado)
    if leilao_id != LEILAO_ID:
        raise HTTPException(404, detail="Leilão não encontrado")


@app.get("/leiloes/{leilao_id}")
def consultar_leilao(leilao_id: int):
    """GET: devolve o estado do leilão (maior lance, quem deu, tempo restante)."""
    _checar_id(leilao_id)
    with _lock:
        return _estado()


@app.get("/leiloes/{leilao_id}/lances")
def listar_lances(leilao_id: int, apos: int = 0):
    """GET usado no polling: devolve só os lances novos (com seq maior que `apos`).

    O participante guarda o seq do último lance que viu e pergunta de tempos em tempos.
    """
    _checar_id(leilao_id)
    with _lock:
        novos = [l for l in _lances if l["seq"] > apos]
        # ultimo_seq deixa o cliente perceber se o servidor reiniciou e voltou a contar do zero
        return {"lances": novos, "ultimo_seq": len(_lances), "status": _estado()["status"]}


@app.post("/leiloes/{leilao_id}/lances", status_code=201)
def dar_lance(leilao_id: int, lance: LanceIn, response: Response):
    """POST: tenta registrar um lance. 201 se aceito, 409 se recusado."""
    _checar_id(leilao_id)
    # Tudo dentro do lock: conferir se o lance é maior e salvar tem que ser uma coisa só.
    # Assim, se dois lances chegam juntos, o primeiro que pegar o lock ganha.
    with _lock:
        if _encerrado():
            raise HTTPException(409, detail={"aceito": False, "motivo": "LEILAO_ENCERRADO"})

        atual = _lances[-1]["valor"] if _lances else None
        minimo = _leilao["lance_minimo"]

        # Recusa se for menor que o mínimo ou não passar do maior lance atual
        if lance.valor < minimo or (atual is not None and lance.valor <= atual):
            raise HTTPException(
                409,
                detail={
                    "aceito": False,
                    "motivo": "LANCE_INSUFICIENTE",
                    "maior_lance_atual": atual,
                    "lance_minimo": minimo,
                },
            )

        # Lance válido: guarda com um número de ordem (seq) e a hora que o servidor recebeu
        novo = {
            "seq": len(_lances) + 1,
            "participante": lance.participante,
            "valor": lance.valor,
            "recebido_em": _agora().isoformat(),
        }
        _lances.append(novo)
        _salvar()  # grava antes de responder, assim um lance aceito não se perde se o servidor cair

    # Boa prática do REST: o cabeçalho Location diz onde o recurso novo está
    response.headers["Location"] = f"/leiloes/{leilao_id}/lances/{novo['seq']}"
    return {"aceito": True, "lance": novo}


def main() -> None:
    # Opções de linha de comando pra configurar o leilão sem mexer no código
    p = argparse.ArgumentParser()
    p.add_argument("--item", default="Notebook usado")
    p.add_argument("--minimo", type=float, default=100.0)
    p.add_argument("--duracao", type=int, default=120, help="segundos até o encerramento")
    p.add_argument("--host", default="0.0.0.0")  # 0.0.0.0 = aceita conexões de outras máquinas
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--arquivo", help="arquivo JSON para salvar o estado e recuperar depois de uma queda")
    a = p.parse_args()

    global _arquivo
    _arquivo = a.arquivo

    # Se já existe um arquivo salvo, o leilão continua de onde parou (ignora --item, --minimo e --duracao)
    if _carregar():
        print(f"Estado recuperado de {_arquivo}: {len(_lances)} lance(s)")
    else:
        _leilao.update(
            item=a.item,
            lance_minimo=a.minimo,
            encerra_em=_agora() + timedelta(seconds=a.duracao),
        )
        _salvar()  # salva já o horário de encerramento, pra ele também sobreviver a uma queda
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
