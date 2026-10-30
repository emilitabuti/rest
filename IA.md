# Registro de uso de IA

Este é um rascunho inicial. O grupo precisa revisar, completar e conferir cada item.

## Ferramentas usadas

- GitHub Copilot (chat no VS Code)

## Principais prompts e o que fizemos com o resultado

Fomos pedindo as coisas por etapas, na ordem em que o trabalho foi andando.

| Etapa | Prompt (resumo) | O que a IA fez | Aproveitado, adaptado ou descartado? |
|---|---|---|---|
| 1. Entender o trabalho | Lemos o PDF do enunciado e pedimos ajuda para fazer a Entrega 1 do grupo REST | Identificou o que a Entrega 1 pede: estudo, design, primeira comunicação, divisão de tarefas e repositório | Aproveitado |
| 2. Estudo da tecnologia | Pedimos um resumo de REST focado em princípios e design, já que todo mundo conhece o uso básico | Explicou as restrições do REST, o problema de não ter push (polling) e vantagens e desvantagens | Aproveitado, mas ainda falta conferir os exemplos de empresas nas fontes oficiais |
| 3. Design da POC | Pedimos o desenho da arquitetura e do formato das mensagens | Propôs as URLs (`/leiloes/1`, `/leiloes/1/lances`), os códigos `201` e `409` e o polling com `?apos=` | Aproveitado |
| 4. Primeira comunicação | Pedimos o código do Leiloeiro e do Participante e um teste com dois processos | Gerou o servidor em FastAPI e o cliente de terminal e rodou os dois para testar | Aproveitado, [ ] falta testar em duas máquinas |
| 5. Repositório e divisão de tarefas | Pedimos o README com a divisão de tarefas e criamos o repositório no GitHub | Escreveu o README com uma divisão sugerida | Adaptado: trocamos as tarefas da Isabela e do Gustavo. O PDF do enunciado ficou fora do repositório |
| 6. Referências | Percebemos que faltavam os links das referências | Colocou os links no README e no `IA.md` | Aproveitado, [ ] falta abrir cada link para conferir |
| 7. Deixar mais simples | Pedimos uma linguagem de estudante nos `.md` e comentários no código | Reescreveu o README e o `IA.md` e comentou o código | Aproveitado |

## O que conferimos na documentação oficial

- [ ] Princípios de REST: [tese de Fielding (2000), cap. 5](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm)
- [ ] Verbos e códigos de status HTTP: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110)
- [ ] Exemplos de empresas: documentação oficial de [GitHub](https://docs.github.com/en/rest), [Stripe](https://docs.stripe.com/api) e [Twilio](https://www.twilio.com/docs/usage/api)
- [ ] FastAPI: [documentação oficial](https://fastapi.tiangolo.com/)

## Um caso em que a IA errou ou sugeriu algo inadequado (obrigatório para o slide)

[ ] _a preencher: contar um caso real que o grupo percebeu e como corrigiu._
