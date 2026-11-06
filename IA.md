# Registro de uso de IA

## Ferramentas usadas

- GitHub Copilot (chat no VS Code)

## Principais prompts e o que fizemos com o resultado

Fomos pedindo as coisas por etapas, na ordem em que o trabalho foi andando.

| Etapa | Prompt (resumo) | O que a IA fez | Aproveitado, adaptado ou descartado? |
|---|---|---|---|
| 1. Entender o trabalho | Lemos o PDF do enunciado e pedimos ajuda para fazer a Entrega 1 do grupo REST | Identificou o que a Entrega 1 pede: estudo, design, primeira comunicação, divisão de tarefas e repositório | Aproveitado |
| 2. Estudo da tecnologia | Pedimos um resumo de REST focado em princípios e design, já que todo mundo conhece o uso básico | Explicou as restrições do REST, o problema de não ter push (polling) e vantagens e desvantagens | Aproveitado |
| 3. Design da POC | Pedimos o desenho da arquitetura e do formato das mensagens | Propôs as URLs (`/leiloes/1`, `/leiloes/1/lances`), os códigos `201` e `409` e o polling com `?apos=` | Aproveitado |
| 4. Primeira comunicação | Pedimos o código do Leiloeiro e do Participante e um teste com dois processos | Gerou o servidor em FastAPI e o cliente de terminal e rodou os dois para testar | Aproveitado, e o grupo testou em duas máquinas |
| 5. Repositório e divisão de tarefas | Pedimos o README com a divisão de tarefas e criamos o repositório no GitHub | Escreveu o README com uma divisão sugerida | Aproveitado |
| 6. Referências | Percebemos que faltavam os links das referências | Colocou os links no README e no `IA.md` | Aproveitado |
| 7. Fase 2: deixar o servidor mais completo | Pedimos a implementação completa, o experimento de falha, o README e os slides | Adicionou a opção `--arquivo` no Leiloeiro (salva o estado em JSON) | Aproveitado |
| 8. Experimentos | Pedimos os experimentos de falha (RE2) e de concorrência (RE3) | Escreveu os scripts da pasta `experimentos/`, rodou e anotou os resultados no README | Aproveitado |
| 9. Correção do polling | O experimento de falha mostrou que o participante ficava mudo depois que o servidor reiniciava | Achou o problema do cursor `seq` e criou o campo `ultimo_seq` | Aproveitado (veja o caso abaixo) |
| 10. Slides | Pedimos os slides do seminário seguindo a estrutura do enunciado | Gerou `slides/leilao_rest.pptx` com um script em Python (python-pptx) e notas do apresentador | Aproveitado, [ ] falta o grupo revisar o texto e o visual |

## O que conferimos na documentação oficial

- [x] Princípios de REST: [tese de Fielding (2000), cap. 5](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm)
- [x] Verbos e códigos de status HTTP: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110)
- [x] Exemplos de empresas: documentação oficial de [GitHub](https://docs.github.com/en/rest), [Stripe](https://docs.stripe.com/api) e [Twilio](https://www.twilio.com/docs/usage/api)
- [x] FastAPI: [documentação oficial](https://fastapi.tiangolo.com/)

## Um caso em que a IA errou ou sugeriu algo inadequado (obrigatório para o slide)

**O erro:** a IA projetou o polling com um cursor: o participante guarda o `seq` do último lance que viu e pergunta só pelos lances com `seq` maior. Ela não pensou no que acontece quando o servidor reinicia sem guardar o estado e volta a contar do `#1`.

**Como percebemos:** no experimento de falha (RE2) sem persistência, o participante que estava acompanhando ficou mudo depois da volta do servidor. O lance novo era o `#1`, menor que o cursor (2), então nunca aparecia.

**Como corrigimos:** o servidor passou a devolver `ultimo_seq` (quantos lances ele tem). Se esse número for menor que o cursor, o cliente avisa que o Leiloeiro reiniciou e recomeça do zero. Rodamos o experimento de novo e o lance novo apareceu.

[ ] _O grupo precisa conferir se entendeu esse caso e conseguir explicar na apresentação._
