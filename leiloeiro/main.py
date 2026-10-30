"""Leiloeiro: servidor REST do leilão (FastAPI)."""
import argparse
import threading
from datetime import datetime, timedelta, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Leilão REST - Leiloeiro")

LEILAO_ID = 1
_lock = threading.Lock()  # lances concorrentes: validação + atualização são atômicas
_leilao: dict = {}
_lances: list[dict] = []  # histórico aceito; seq é a ordem total definida pelo servidor


class LanceIn(BaseModel):
    participante: str = Field(min_length=1)
    valor: float = Field(gt=0)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _encerrado() -> bool:
    return _agora() >= _leilao["encerra_em"]


def _estado() -> dict:
    encerrado = _encerrado()
    maior = _lances[-1] if _lances else None
    restante = max(0.0, (_leilao["encerra_em"] - _agora()).total_seconds())
    return {
        "id": LEILAO_ID,
        "item": _leilao["item"],
        "lance_minimo": _leilao["lance_minimo"],
        "maior_lance": maior,
        "encerra_em": _leilao["encerra_em"].isoformat(),
        "tempo_restante_s": round(restante, 1),
        "status": "ENCERRADO" if encerrado else "ABERTO",
        "vencedor": (maior["participante"] if maior else None) if encerrado else None,
    }


def _checar_id(leilao_id: int) -> None:
    if leilao_id != LEILAO_ID:
        raise HTTPException(404, detail="Leilão não encontrado")


@app.get("/leiloes/{leilao_id}")
def consultar_leilao(leilao_id: int):
    _checar_id(leilao_id)
    with _lock:
        return _estado()


@app.get("/leiloes/{leilao_id}/lances")
def listar_lances(leilao_id: int, apos: int = 0):
    """Polling incremental: devolve só os lances com seq > `apos`."""
    _checar_id(leilao_id)
    with _lock:
        return {"lances": [l for l in _lances if l["seq"] > apos], "status": _estado()["status"]}


@app.post("/leiloes/{leilao_id}/lances", status_code=201)
def dar_lance(leilao_id: int, lance: LanceIn, response: Response):
    _checar_id(leilao_id)
    with _lock:
        if _encerrado():
            raise HTTPException(409, detail={"aceito": False, "motivo": "LEILAO_ENCERRADO"})
        atual = _lances[-1]["valor"] if _lances else None
        minimo = _leilao["lance_minimo"]
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
        novo = {
            "seq": len(_lances) + 1,
            "participante": lance.participante,
            "valor": lance.valor,
            "recebido_em": _agora().isoformat(),
        }
        _lances.append(novo)
    response.headers["Location"] = f"/leiloes/{leilao_id}/lances/{novo['seq']}"
    return {"aceito": True, "lance": novo}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--item", default="Notebook usado")
    p.add_argument("--minimo", type=float, default=100.0)
    p.add_argument("--duracao", type=int, default=120, help="segundos até o encerramento")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()
    _leilao.update(
        item=a.item,
        lance_minimo=a.minimo,
        encerra_em=_agora() + timedelta(seconds=a.duracao),
    )
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
