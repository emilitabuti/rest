# Leilão Distribuído com REST

Projeto de **Sistemas Distribuídos e Computação Paralela** 

**Tecnologia para o Grupo 7: REST / RESTful.**

> **Situação:** Entrega 2 (POC completa, experimentos, README e slides em `slides/`).

**Integrantes:** Caroline Guimarães Campos, Emili Vieira Tabuti, Gustavo Macedo Costa, Isabela Groke Gomes.

---

## 1. Estudo da tecnologia

### 1.1 O que é REST

REST (*Representational State Transfer*) **não é um protocolo nem uma biblioteca**. É um **jeito de organizar** a comunicação entre sistemas, ou seja, um estilo de arquitetura. Ele foi proposto por Roy Fielding na [tese de doutorado dele, em 2000](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm).

Na prática, o REST usa o HTTP (o mesmo da web). O servidor mostra **recursos** (coisas como "leilão" ou "lance"), cada um com sua URL. O cliente usa os **verbos HTTP** (GET, POST...) para ler ou criar esses recursos, trocando dados em JSON.

Dentro do que vimos na disciplina, o REST é um **Web Service**. A comunicação é **síncrona** (o cliente manda e espera a resposta), **direta** (o cliente conhece o endereço do servidor) e do tipo **requisição/resposta**.

### 1.2 Os princípios do REST

| Princípio | O que quer dizer | Como aparece no nosso leilão |
|---|---|---|
| Cliente/servidor | Cada lado cuida do seu trabalho e os dois podem mudar sem afetar o outro | O Participante e o Leiloeiro só combinam o formato das requisições e do JSON |
| **Sem estado (stateless)** | Cada requisição leva tudo o que o servidor precisa. O servidor não guarda "sessão" do cliente | O participante manda o nome em cada lance. Não existe login |
| Cache | As respostas podem dizer se dá para reaproveitar | O `GET` não altera nada, então poderia usar cache |
| **Interface uniforme** | URLs para recursos, verbos com significado fixo e códigos de status padronizados | `/leiloes/1` e `/leiloes/1/lances`, com `201`, `409` etc. |
| Camadas | O cliente não sabe se está falando direto com o servidor ou com um proxy no meio | Dá para colocar um proxy ou Docker na frente sem mudar o cliente |
| Código sob demanda (opcional) | O servidor pode mandar código para o cliente executar | Não usamos |

Coisas importantes de design que vamos seguir:

- **Substantivo na URL, ação no verbo.** Usamos `POST /leiloes/1/lances` ("cria um lance") e não `/darLance`.
- **Verbos:** `GET` só lê e pode ser repetido sem problema (idempotente). `POST` **não** é idempotente: se repetir, cria outro lance. `PUT` e `DELETE` são idempotentes.
- **Os códigos de status fazem parte do contrato:** `201 Created` (lance aceito), `409 Conflict` (lance recusado porque conflita com o estado atual), `404` (não achou), `422` (JSON inválido).
- **[Modelo de maturidade de Richardson](https://martinfowler.com/articles/richardsonMaturityModel.html):** nível 0 (só HTTP como túnel), 1 (recursos), 2 (verbos e status corretos), 3 (links nas respostas, o HATEOAS). A nossa POC fica no **nível 2**, que é o que a maioria das APIs "REST" usa de verdade.

### 1.3 Como o REST resolve o leilão, e o problema dele

O leilão tem dois tipos de interação:

- **Dar um lance e saber se foi aceito:** combina muito bem com REST (`POST` e o status da resposta).
- **Ficar sabendo dos lances dos outros:** aqui o REST tem uma limitação. **O servidor nunca começa a conversa**, então não existe "push". O participante precisa **perguntar de tempos em tempos** (isso se chama *polling*).

Esse é o ponto que vamos destacar no seminário em comparação com WebSocket, gRPC (streaming) e MOM (publish/subscribe). No REST, **quem puxa a informação é o cliente**. O custo disso é que a notícia pode demorar até um intervalo de polling para chegar, e muitas perguntas voltam sem novidade.

Formas de melhorar: pedir só os lances novos (`?apos=seq`, que vamos usar), `ETag`/`304 Not Modified`, *long polling*. Fora do REST puro existem SSE, WebSocket e webhooks.

### 1.4 Vantagens, desvantagens e onde é usado

| Vantagens | Desvantagens |
|---|---|
| Simples e funciona em qualquer linguagem que fale HTTP | Não tem push, só polling |
| Fácil de testar (`curl`, navegador) | JSON em texto é mais pesado que o Protocol Buffers do gRPC |
| Pouco acoplamento: o contrato é só URL + JSON | O contrato não é tão rígido quanto um WSDL ou um `.proto` (o OpenAPI ajuda) |
| Sem estado, então é fácil escalar com vários servidores | Quem decide a ordem dos lances e a concorrência é o servidor |
| Aproveita o que já existe do HTTP (cache, proxy, TLS) | |

**Quem usa:** as APIs públicas do [GitHub](https://docs.github.com/en/rest), [Stripe](https://docs.stripe.com/api), [Twilio](https://www.twilio.com/docs/usage/api) e [Google Maps](https://developers.google.com/maps/documentation), além de muitas APIs de e-commerce e pagamento. Conferimos os links e os exemplos na documentação oficial de cada API (regra da Seção 9 do enunciado).

**Ferramentas:** [FastAPI](https://fastapi.tiangolo.com/) (a que escolhemos), Flask, Spring Boot, Express, [OpenAPI](https://spec.openapis.org/oas/latest.html)/Swagger, Postman e curl.

---

## 2. Design da POC

### 2.1 Arquitetura

```mermaid
flowchart LR
    subgraph M1["Máquina A"]
        L["Leiloeiro<br/>FastAPI + uvicorn<br/>porta 8000"]
    end
    subgraph M2["Máquina B"]
        P1["Participante 1<br/>cliente de terminal"]
        P2["Participante 2<br/>cliente de terminal"]
    end
    P1 -- "POST /leiloes/1/lances" --> L
    P2 -- "POST /leiloes/1/lances" --> L
    P1 -. "GET /leiloes/1/lances?apos=N (polling)" .-> L
    P2 -. "GET /leiloes/1/lances?apos=N (polling)" .-> L
```

- **Quem começa a conversa:** sempre o Participante (o cliente). O Leiloeiro nunca fala primeiro.
- **Leiloeiro** ([leiloeiro/main.py](leiloeiro/main.py)): guarda o leilão e os lances **na memória** (ou em um arquivo JSON, se usar `--arquivo`) e usa um `Lock` para tratar um lance de cada vez.
- **Participante** ([participante/cliente.py](participante/cliente.py)): programa de terminal com os comandos `consultar`, `lance` e `acompanhar` (polling). Se o servidor ficar fora do ar, ele avisa e continua tentando.
- Linguagem: Python 3.12. Transporte: HTTP. Formato dos dados: JSON.

### 2.2 Decisões que tomamos (e por quê)

1. **O fim do leilão é calculado na hora.** Não tem timer: se a hora atual passou da hora de encerramento, o leilão está `ENCERRADO`. Isso evita bug de timer disputando com um lance.
2. **Vale o relógio do servidor.** Só o Leiloeiro decide se o leilão acabou e a que horas cada lance chegou (`recebido_em`). O participante não manda horário. Isso liga com a aula de sincronização de relógios.
3. **Cada lance aceito ganha um número de ordem (`seq`).** O polling usa `?apos=seq`, então o participante não perde nem repete lances.
4. **Lance recusado volta como `409 Conflict`** e não `400`. O pedido está escrito certo, mas conflita com o estado atual do leilão. O corpo da resposta explica o motivo.
5. **Concorrência:** conferir "o valor é maior que o atual?" e salvar o lance acontecem juntos dentro de um `Lock`. Se dois lances chegam ao mesmo tempo, **o primeiro que pegar o lock ganha** e o outro recebe `409`. Vamos medir isso no RE3.
6. **Um leilão por execução** (configurado por parâmetros), mas a URL já é `/leiloes/{id}`, então dá para ter vários leilões depois.

### 2.3 API e formato das mensagens (RF6)

| Operação | Requisição | Resposta |
|---|---|---|
| Consultar o leilão (RF2) | `GET /leiloes/1` | `200` com o estado |
| Dar lance (RF3) | `POST /leiloes/1/lances` | `201` aceito ou `409` recusado |
| Ver lances novos (RF4, polling) | `GET /leiloes/1/lances?apos=N` | `200` com a lista de novos |

**Consultar o leilão** devolve `200 OK`:
```json
{
  "id": 1,
  "item": "Notebook usado",
  "lance_minimo": 100.0,
  "maior_lance": {"seq": 2, "participante": "Bia", "valor": 200.0, "recebido_em": "2026-10-30T13:04:30.798543+00:00"},
  "encerra_em": "2026-10-30T13:04:42.000000+00:00",
  "tempo_restante_s": 10.7,
  "status": "ABERTO",
  "vencedor": null
}
```
O campo `vencedor` só vem preenchido quando o `status` é `ENCERRADO` (RF5).

**Dar lance.** O corpo da requisição é:
```json
{"participante": "Ana", "valor": 150.0}
```
Se aceito, volta `201 Created` com o cabeçalho `Location: /leiloes/1/lances/1`:
```json
{"aceito": true, "lance": {"seq": 1, "participante": "Ana", "valor": 150.0, "recebido_em": "..."}}
```
Se recusado, volta `409 Conflict`:
```json
{"detail": {"aceito": false, "motivo": "LANCE_INSUFICIENTE", "maior_lance_atual": 150.0, "lance_minimo": 100.0}}
```
```json
{"detail": {"aceito": false, "motivo": "LEILAO_ENCERRADO"}}
```

**Ver lances novos** devolve `200 OK`:
```json
{"lances": [{"seq": 3, "participante": "Ana", "valor": 250.0, "recebido_em": "..."}], "ultimo_seq": 3, "status": "ABERTO"}
```

O campo `ultimo_seq` é quantos lances o servidor tem. O cliente usa ele para perceber que o servidor reiniciou e perdeu os lances (veja o RE2).

O FastAPI gera sozinho uma documentação interativa (OpenAPI) em `http://<ip-do-leiloeiro>:8000/docs`.

### 2.4 Requisitos do enunciado

| Requisito | Situação | Como |
|---|---|---|
| RF1: 1 Leiloeiro e 2 ou mais Participantes em processos separados | OK (testamos com 2 processos) | Servidor e cliente rodam em terminais diferentes |
| RF2: ver o estado do leilão | OK | `GET /leiloes/1` |
| RF3: dar lance (aceito/recusado) | OK | `POST` com `201` ou `409` |
| RF4: notificação | OK (testado com 2 participantes acompanhando, seção 5.3) | Polling com `?apos=` |
| RF5: encerramento e vencedor | OK | Campo `vencedor` e recusa com `LEILAO_ENCERRADO` |
| RF6: formato das mensagens | OK | Seção 2.3 |
| RE1: rodar em 2 máquinas | OK (seção 5.4) | Usar `--url http://IP:8000` |
| RE2: experimento de falha | OK | Seção 5.1 |
| RE3: experimento de concorrência | OK | Seção 5.2 |
| RE4: repositório com README | OK | Este README |

---

## 3. Primeira comunicação entre dois processos

Já funciona: um Participante manda um lance e o Leiloeiro responde se foi **aceito ou recusado**. Esta é a saída do nosso teste (leilão de 15 segundos, lance mínimo 100):

```
$ python participante/cliente.py lance Ana 50
RECUSADO: {'aceito': False, 'motivo': 'LANCE_INSUFICIENTE', 'maior_lance_atual': None, 'lance_minimo': 100.0}
$ python participante/cliente.py lance Ana 150
ACEITO: {'seq': 1, 'participante': 'Ana', 'valor': 150.0, ...}
$ python participante/cliente.py lance Bia 150
RECUSADO: {'aceito': False, 'motivo': 'LANCE_INSUFICIENTE', 'maior_lance_atual': 150.0, ...}
$ python participante/cliente.py lance Bia 200
ACEITO: {'seq': 2, 'participante': 'Bia', 'valor': 200.0, ...}
(depois que o leilão acabou)
$ python participante/cliente.py lance Ana 999
RECUSADO: {'aceito': False, 'motivo': 'LEILAO_ENCERRADO'}
$ python participante/cliente.py consultar
[ENCERRADO] Notebook usado | mínimo: 100.0 | restante: 0.0s
  maior lance: 200.0 por Bia
  VENCEDOR: Bia
```

---

## 4. Como executar

Precisa de Python 3.10 ou mais novo.

```bash
git clone https://github.com/emilitabuti/rest.git && cd rest
python3 -m venv .venv
source .venv/bin/activate            # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Máquina A (Leiloeiro):**
```bash
python leiloeiro/main.py --item "Notebook usado" --minimo 100 --duracao 120 --port 8000
```
Veja o IP da máquina com `hostname -I`. Se precisar, libere a porta 8000 no firewall.

Para o servidor **não perder os lances se cair**, use `--arquivo`. Ao ligar de novo com o mesmo arquivo, o leilão continua de onde parou (inclusive o horário de encerramento):
```bash
python leiloeiro/main.py --arquivo leilao.json
```

**Máquina B (Participantes, um terminal para cada):**
```bash
python participante/cliente.py --url http://IP_DA_MAQUINA_A:8000 acompanhar
python participante/cliente.py --url http://IP_DA_MAQUINA_A:8000 consultar
python participante/cliente.py --url http://IP_DA_MAQUINA_A:8000 lance Ana 150
```
Se não colocar `--url`, ele usa `http://localhost:8000`.

Também dá para testar sem o cliente, só com o curl:
`curl -X POST localhost:8000/leiloes/1/lances -H 'Content-Type: application/json' -d '{"participante":"Ana","valor":150}'`

---

## 5. Experimentos

Os experimentos RE2 e RE3 foram rodados em uma máquina só (`localhost`), com os scripts da pasta [experimentos/](experimentos/). O teste em duas máquinas (RE1) está na seção 5.4.

### 5.1 RE2: o Leiloeiro cai no meio do leilão

O script sobe o servidor, dá dois lances (Ana 150 e Bia 200), deixa um participante acompanhando, derruba o servidor com `kill`, liga de novo e dá um lance de 250:

```bash
python experimentos/falha.py            # servidor só em memória
python experimentos/falha.py --salvar   # servidor com --arquivo
```

| O que aconteceu | Servidor só em memória | Servidor com `--arquivo` |
|---|---|---|
| Dar lance com o servidor fora do ar | Erro de conexão (`Connection refused`) | Erro de conexão |
| Participante acompanhando | Avisa "Leiloeiro indisponível" e continua tentando | Igual |
| Depois de reiniciar | Leilão **sem lances** e com prazo novo (~60 s). O maior lance **se perdeu** | **Maior lance preservado** (200, Bia) e o prazo continua |
| Lance de 250 depois da volta | Vira o lance `#1` | Vira o lance `#3` |

**Explicação:** no REST o servidor não guarda "conversa" com o cliente, mas o **estado do leilão** mora no Leiloeiro. Se ele cai e não salvou nada, o leilão se perde. O Leiloeiro é um **ponto único de falha**. Salvando em arquivo, o leilão sobrevive a uma queda. O cliente aguenta a queda sozinho porque o polling é só repetir a pergunta.

**Um bug que o experimento mostrou:** na primeira versão, o participante usava o `seq` do último lance que viu (2) como cursor. Depois do reinício sem persistência, o novo lance era o `#1`, menor que o cursor, então o participante **não via o lance novo** e ficava mudo. Corrigimos com o campo `ultimo_seq`: se o servidor tem menos lances do que o cliente já viu, o cliente avisa e recomeça do zero. Saída depois da correção:

```
NOVO LANCE #1: 150.0 por Ana
NOVO LANCE #2: 200.0 por Bia
Leiloeiro indisponível (ConnectionError); tentando de novo...
O Leiloeiro reiniciou e perdeu os lances. Começando a acompanhar do zero.
NOVO LANCE #1: 250.0 por Ana
```

### 5.2 RE3: dois lances ao mesmo tempo

O script usa threads e uma barreira para soltar 5 lances do mesmo valor no mesmo instante:

```bash
python experimentos/concorrencia.py --participantes 5 --valor 500
```

```
5 participantes deram o lance 500.0 ao mesmo tempo:
  P1: HTTP 409
  P2: HTTP 409
  P3: HTTP 409
  P4: HTTP 409
  P5: HTTP 201
Aceitos: 1 | Recusados: 4
OK: só um lance foi aceito.
```

Numa segunda rodada (valor 600), quem ganhou foi o P1. **Sempre só um lance é aceito, mas quem ganha muda de uma rodada para outra.**

**Explicação:** conferir "o valor é maior que o atual?" e gravar o lance acontecem juntos dentro de um `Lock`. Quem pega o lock primeiro é aceito, e os outros já encontram o valor atualizado e recebem `409`. Quem foi "primeiro" é decidido **pela ordem de chegada no servidor**, não pelo relógio do cliente. Isso mostra, na prática, o problema de ordenar eventos em sistemas distribuídos.

### 5.3 RF4: dois participantes acompanhando

Com dois `acompanhar` rodando em terminais diferentes, os dois viram exatamente os mesmos lances e o mesmo vencedor:

```
--- Participante 1:                       --- Participante 2:
NOVO LANCE #1: 150.0 por Ana              NOVO LANCE #1: 150.0 por Ana
NOVO LANCE #2: 200.0 por Bia              NOVO LANCE #2: 200.0 por Bia
Leilão encerrado.                         Leilão encerrado.
  VENCEDOR: Bia                             VENCEDOR: Bia
```

O lance de 180 da Ana foi recusado (`409`), porque o maior já era 200, e por isso ninguém foi notificado dele. Como é polling, cada participante descobre o lance novo só na próxima pergunta, então o atraso máximo é o intervalo (`--intervalo`, padrão 1 s).

### 5.4 RE1: rodando em duas máquinas

Rodamos o Leiloeiro em uma máquina e os Participantes em outra, na mesma rede, em 06/11/2026.

- **IP usado:** `172.17.15.19`
- **Porta:** `8000`
- **Comandos:** os mesmos da seção 4, com `--url http://172.17.15.19:8000` nos Participantes.

Resultado: o lance aceito, o lance recusado e a notificação de novo lance (polling) funcionaram entre as duas máquinas, do mesmo jeito que em `localhost`. Como o servidor escuta em `0.0.0.0`, não foi preciso mudar nada no código para sair de uma máquina para duas. Gravamos um vídeo curto dessa demonstração como plano B para o seminário.

---

## 6. Divisão de tarefas (proposta, o grupo pode ajustar)

| Integrante | Responsabilidade principal | Entregas |
|---|---|---|
| Emili Vieira Tabuti | **Leiloeiro** (API, regras de lance, encerramento) | `leiloeiro/`, persistência (`--arquivo`) |
| Isabela Groke Gomes | **Participante** (cliente de terminal, polling, tratamento de falha) | `participante/`, reconexão |
| Gustavo Macedo Costa | **Experimentos RE2 e RE3**, teste em 2 máquinas (RE1) e vídeo de plano B | Seção 5, script de concorrência |
| Caroline Guimarães Campos | **Estudo e slides** (partes 1, 2 e 7), diagrama e `IA.md` | Seção 1, slides |

Todo mundo precisa saber explicar qualquer parte do código (regra da Seção 9 do enunciado). Por isso vamos **revisar o código uns dos outros** antes do seminário.

## 7. O que ainda falta antes do seminário (13/11)

- [ ] Ler o `IA.md` e os slides, e ajustar o que não bater com o que o grupo realmente fez.
- [ ] **Todo mundo** treinar a explicação de qualquer parte do código (o professor escolhe quem responde).
- [ ] Combinar quem apresenta cada slide (sugestão nas notas do apresentador dos slides).

Extras que sobraram: medir o tempo entre o lance e a notificação (depende do intervalo de polling), Docker e interface web.

## 8. Referências

- Fielding, R. T. [*Architectural Styles and the Design of Network-based Software Architectures*](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm) (2000), cap. 5: REST.
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) (métodos, idempotência e códigos de status).
- Fowler, M. [Richardson Maturity Model](https://martinfowler.com/articles/richardsonMaturityModel.html).
- [FastAPI](https://fastapi.tiangolo.com/) e [OpenAPI Specification](https://spec.openapis.org/oas/latest.html).
- Exemplos de APIs REST: [GitHub](https://docs.github.com/en/rest), [Stripe](https://docs.stripe.com/api), [Twilio](https://www.twilio.com/docs/usage/api), [Google Maps](https://developers.google.com/maps/documentation).
- Slides da disciplina (Prof. Carlos Paes); Coulouris et al., *Sistemas Distribuídos: conceitos e projeto*, 5. ed.; Tanenbaum e Van Steen, *Sistemas Distribuídos: princípios e paradigmas*, 2. ed.

## 9. Estrutura do repositório

```
leiloeiro/main.py            servidor REST
participante/cliente.py      cliente de terminal
experimentos/falha.py        experimento RE2 (queda do Leiloeiro)
experimentos/concorrencia.py experimento RE3 (lances simultâneos)
slides/leilao_rest.pptx      slides do seminário
slides/gerar_slides.py       script que gera os slides
requirements.txt             dependências
IA.md                        registro do uso de IA
README.md                    este arquivo
```
Os slides têm notas do apresentador. Para gerar de novo: `pip install -r slides/requirements.txt` e `python slides/gerar_slides.py`.
