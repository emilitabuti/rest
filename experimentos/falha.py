"""Experimento RE2: derrubar o Leiloeiro no meio do leilão e ligar de novo.

Roda tudo sozinho, na mesma máquina (sobe o servidor, dá lances, derruba, reinicia):
    python experimentos/falha.py            # servidor SÓ NA MEMÓRIA
    python experimentos/falha.py --salvar   # servidor com --arquivo (salva em disco)
"""
import argparse
import os
import subprocess
import sys
import tempfile
import threading
import time

import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://localhost:8765"


def subir_servidor(arquivo: str | None) -> subprocess.Popen:
    cmd = [sys.executable, os.path.join(RAIZ, "leiloeiro", "main.py"), "--duracao", "60", "--port", "8765"]
    if arquivo:
        cmd += ["--arquivo", arquivo]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):  # espera o servidor ficar pronto (até uns 10 s)
        try:
            requests.get(f"{URL}/leiloes/1", timeout=1)
            return proc
        except requests.RequestException:
            time.sleep(0.2)
    proc.kill()
    sys.exit("Servidor não subiu")


def cliente(*args: str) -> str:
    cmd = [sys.executable, os.path.join(RAIZ, "participante", "cliente.py"), "--url", URL, *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--salvar", action="store_true", help="usa --arquivo no servidor")
    args = p.parse_args()

    pasta = tempfile.mkdtemp()
    arquivo = os.path.join(pasta, "leilao.json") if args.salvar else None
    print(f"=== RE2: servidor {'COM' if args.salvar else 'SEM'} persistência ===")

    servidor = subir_servidor(arquivo)
    print("1) Servidor no ar. Dois lances:")
    print("  ", cliente("lance", "Ana", "150"))
    print("  ", cliente("lance", "Bia", "200"))

    # Participante acompanhando o leilão em outro processo, guardando o que ele imprime
    watcher = subprocess.Popen(
        [sys.executable, "-u", os.path.join(RAIZ, "participante", "cliente.py"), "--url", URL,
         "acompanhar", "--intervalo", "0.5"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    saida: list[str] = []
    threading.Thread(target=lambda: [saida.append(l.strip()) for l in watcher.stdout], daemon=True).start()
    time.sleep(1.5)

    print("2) Derrubando o Leiloeiro (kill)...")
    servidor.kill()
    servidor.wait()
    time.sleep(1.5)
    print("   Dar lance com o servidor fora do ar:")
    print("  ", cliente("lance", "Ana", "250"))

    print("3) Ligando o Leiloeiro de novo...")
    servidor = subir_servidor(arquivo)
    print("   Estado depois de reiniciar:")
    print("  ", cliente("consultar").replace("\n", "\n   "))
    print("   Novo lance de 250 (Ana):")
    print("  ", cliente("lance", "Ana", "250"))
    time.sleep(1.5)

    print("4) O que o participante que estava acompanhando imprimiu:")
    vistos = []
    for linha in saida:
        if linha not in vistos or "indisponível" not in linha:  # não repete o aviso 20 vezes
            vistos.append(linha)
    for linha in vistos:
        print("  ", linha)

    watcher.kill()
    servidor.kill()


if __name__ == "__main__":
    main()
