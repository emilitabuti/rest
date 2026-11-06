"""Participante: cliente de linha de comando do leilão REST."""
import argparse
import sys
import time

import requests


def consultar(base: str) -> None:
    """Mostra o estado atual do leilão (GET /leiloes/1)."""
    r = requests.get(f"{base}/leiloes/1", timeout=5)  # timeout evita ficar esperando pra sempre
    r.raise_for_status()  # levanta erro se o status for 4xx ou 5xx
    e = r.json()
    maior = e["maior_lance"]
    print(f"[{e['status']}] {e['item']} | mínimo: {e['lance_minimo']} | restante: {e['tempo_restante_s']}s")
    print(f"  maior lance: {maior['valor']} por {maior['participante']}" if maior else "  sem lances")
    if e["vencedor"]:
        print(f"  VENCEDOR: {e['vencedor']}")


def lance(base: str, nome: str, valor: float) -> None:
    """Envia um lance (POST /leiloes/1/lances) e mostra se foi aceito ou recusado."""
    r = requests.post(f"{base}/leiloes/1/lances", json={"participante": nome, "valor": valor}, timeout=5)
    if r.status_code == 201:  # 201 = lance criado, ou seja, aceito
        print(f"ACEITO: {r.json()['lance']}")
    elif r.status_code == 409:  # 409 = conflito, ou seja, recusado (valor baixo ou leilão fechado)
        print(f"RECUSADO: {r.json()['detail']}")
    else:
        print(f"ERRO {r.status_code}: {r.text}")


def acompanhar(base: str, intervalo: float) -> None:
    """Polling: pergunta ao servidor, de tempos em tempos, se tem lance novo.

    No REST o servidor não avisa ninguém, então o cliente é que precisa ficar perguntando.
    """
    ultimo = 0  # seq do último lance que já mostramos
    while True:
        try:
            r = requests.get(f"{base}/leiloes/1/lances", params={"apos": ultimo}, timeout=5)
            r.raise_for_status()
            dados = r.json()
        except requests.RequestException as exc:
            # Servidor fora do ar: avisa e tenta de novo, sem fechar o programa
            print(f"Leiloeiro indisponível ({type(exc).__name__}); tentando de novo...")
            time.sleep(intervalo)
            continue

        if dados["ultimo_seq"] < ultimo:
            # O servidor tem menos lances do que eu já vi: ele reiniciou sem guardar o estado
            print("O Leiloeiro reiniciou e perdeu os lances. Começando a acompanhar do zero.")
            ultimo = 0
            continue

        for l in dados["lances"]:
            print(f"NOVO LANCE #{l['seq']}: {l['valor']} por {l['participante']}")
            ultimo = l["seq"]

        if dados["status"] == "ENCERRADO":
            print("Leilão encerrado.")
            consultar(base)  # mostra o vencedor
            return
        time.sleep(intervalo)  # espera um pouco antes de perguntar de novo


def main() -> None:
    # Comandos: consultar | lance <nome> <valor> | acompanhar
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000", help="endereço do Leiloeiro")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("consultar")
    l = sub.add_parser("lance")
    l.add_argument("nome")
    l.add_argument("valor", type=float)
    a = sub.add_parser("acompanhar")
    a.add_argument("--intervalo", type=float, default=1.0, help="segundos entre cada pergunta")
    args = p.parse_args()

    try:
        if args.cmd == "consultar":
            consultar(args.url)
        elif args.cmd == "lance":
            lance(args.url, args.nome, args.valor)
        else:
            acompanhar(args.url, args.intervalo)
    except requests.RequestException as exc:
        # Não conseguiu falar com o servidor (desligado, IP errado, firewall...)
        sys.exit(f"Falha ao falar com o Leiloeiro: {exc}")


if __name__ == "__main__":
    main()
