"""Experimento RE3: vários participantes dão o MESMO lance ao mesmo tempo.

Uso (com o Leiloeiro já rodando):
    python experimentos/concorrencia.py --url http://localhost:8000 --participantes 5 --valor 500
"""
import argparse
import threading

import requests


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--participantes", type=int, default=5)
    p.add_argument("--valor", type=float, default=500.0)
    args = p.parse_args()

    # A barreira segura todas as threads até a última chegar, e aí solta todas juntas
    barreira = threading.Barrier(args.participantes)
    resultados = []

    def disparar(nome: str) -> None:
        sessao = requests.Session()
        barreira.wait()
        r = sessao.post(
            f"{args.url}/leiloes/1/lances",
            json={"participante": nome, "valor": args.valor},
            timeout=10,
        )
        resultados.append((nome, r.status_code, r.json()))

    threads = [threading.Thread(target=disparar, args=(f"P{i + 1}",)) for i in range(args.participantes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"{args.participantes} participantes deram o lance {args.valor} ao mesmo tempo:")
    for nome, status, corpo in sorted(resultados):
        print(f"  {nome}: HTTP {status}")
    aceitos = [r for r in resultados if r[1] == 201]
    print(f"Aceitos: {len(aceitos)} | Recusados: {len(resultados) - len(aceitos)}")
    if aceitos:
        print(f"Vencedor do lance: {aceitos[0][0]} (seq {aceitos[0][2]['lance']['seq']})")

    estado = requests.get(f"{args.url}/leiloes/1", timeout=5).json()
    print(f"Maior lance no servidor: {estado['maior_lance']}")
    print("OK: só um lance foi aceito." if len(aceitos) == 1 else "ATENÇÃO: mais de um lance aceito!")


if __name__ == "__main__":
    main()
