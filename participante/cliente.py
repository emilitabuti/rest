"""Participante: cliente de linha de comando do leilão REST."""
import argparse
import sys
import time

import requests


def consultar(base: str) -> None:
    r = requests.get(f"{base}/leiloes/1", timeout=5)
    r.raise_for_status()
    e = r.json()
    maior = e["maior_lance"]
    print(f"[{e['status']}] {e['item']} | mínimo: {e['lance_minimo']} | restante: {e['tempo_restante_s']}s")
    print(f"  maior lance: {maior['valor']} por {maior['participante']}" if maior else "  sem lances")
    if e["vencedor"]:
        print(f"  VENCEDOR: {e['vencedor']}")


def lance(base: str, nome: str, valor: float) -> None:
    r = requests.post(f"{base}/leiloes/1/lances", json={"participante": nome, "valor": valor}, timeout=5)
    if r.status_code == 201:
        print(f"ACEITO: {r.json()['lance']}")
    elif r.status_code == 409:
        print(f"RECUSADO: {r.json()['detail']}")
    else:
        print(f"ERRO {r.status_code}: {r.text}")


def acompanhar(base: str, intervalo: float) -> None:
    ultimo = 0
    while True:
        try:
            r = requests.get(f"{base}/leiloes/1/lances", params={"apos": ultimo}, timeout=5)
            r.raise_for_status()
            dados = r.json()
        except requests.RequestException as exc:
            print(f"Leiloeiro indisponível ({type(exc).__name__}); tentando de novo...")
            time.sleep(intervalo)
            continue
        for l in dados["lances"]:
            print(f"NOVO LANCE #{l['seq']}: {l['valor']} por {l['participante']}")
            ultimo = l["seq"]
        if dados["status"] == "ENCERRADO":
            print("Leilão encerrado.")
            consultar(base)
            return
        time.sleep(intervalo)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000", help="endereço do Leiloeiro")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("consultar")
    l = sub.add_parser("lance")
    l.add_argument("nome")
    l.add_argument("valor", type=float)
    a = sub.add_parser("acompanhar")
    a.add_argument("--intervalo", type=float, default=1.0)
    args = p.parse_args()
    try:
        if args.cmd == "consultar":
            consultar(args.url)
        elif args.cmd == "lance":
            lance(args.url, args.nome, args.valor)
        else:
            acompanhar(args.url, args.intervalo)
    except requests.RequestException as exc:
        sys.exit(f"Falha ao falar com o Leiloeiro: {exc}")


if __name__ == "__main__":
    main()
