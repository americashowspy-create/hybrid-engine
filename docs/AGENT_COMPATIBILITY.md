# Compatibilidade de agentes — Codex, ChatGPT, Claude Code e IDEs

**Versão candidata: 0.11.1.** O Hybrid Engine é um protocolo e uma CLI Python
opcional; **não é um plugin embutido, um modelo de IA, nem uma autorização
automática para acessar dados, executar comandos ou criar PRs**.

## Passo 1 — definir as duas coisas separadamente

- **Framework:** `https://github.com/americashowspy-create/hybrid-engine`.
- **Alvo:** repositório ou diretório do projeto que a pessoa realmente controla.

Peça ao agente para confirmar o alvo e o commit examinados. Uma URL pode ser lida
como texto, mas isso não prova que o agente carregou os arquivos do Hybrid.

## Passo 2 — confirmar ferramentas reais

Antes de atribuir um resultado à ferramenta, confirmar:

1. `AGENTS.md` e `docs/PROJECT_AUDIT.md` foram lidos de fato?
2. A árvore local do alvo está acessível?
3. Existe Python 3.11+ com `hybrid_engine` executável?
4. Qual comando foi executado, com que diretório e qual código de saída?
5. Há relatório no caminho indicado, fora da árvore do alvo?

Quando o comando `project-audit` atingir o limite de 250 arquivos, a candidata
0.11.1 executa **automaticamente** lotes adicionais, quando o orçamento permite.
Confirme `workspace.coverage` e `workspace.partitions`. O `assessment` inicial
pode permanecer `INCOMPLETE`, e seu `advisor` permanecer `BLOCKED`: são estados
verdadeiros daquela passagem. A conclusão dos lotes não demonstra ciclos de
imports entre lotes nem segurança de produção. Não invente logs, SHAs, permissões
ou testes não executados.

## Passo 3 — pedido inicial seguro e claro

```text
Quero usar o Hybrid Engine público:
https://github.com/americashowspy-create/hybrid-engine

Alvo: o projeto local que tenho aberto e que estou autorizado a revisar.

Leia AGENTS.md e docs/PROJECT_AUDIT.md do framework.
Confirme qual repositório e commit do alvo você consegue examinar.
Faça revisão estática e somente leitura de arquitetura, código,
dependências, banco e práticas defensivas.
Se houver acesso ao terminal, use project-audit e mostre cobertura,
limites, lotes e evidências reais.
Não faça pentest ativo, varredura externa, acesso à produção,
alterações no código, banco, credenciais, merge ou deploy.
Se alguma atividade exigir permissões adicionais, respeite a restrição
e informe exatamente o que ficou não verificado.
```

## E se o agente mencionar Daybreak ou negar a atividade?

Uma solicitação de revisão de segurança pode ser interpretada de maneira mais
ampla que uma simples inspeção estática. **A presença do Hybrid Engine não prova
a causa de uma recusa.** Colete, sem segredos:

- prompt inicial e trecho exato da mensagem de restrição;
- se o agente conseguiu ler o framework e o projeto alvo;
- comandos realmente tentados e suas saídas, se existirem;
- etapa em que ocorreu o bloqueio e atividades que permaneceram permitidas.

**Não reformule pedidos para driblar controles de segurança.** Para tarefas
que a plataforma efetivamente permite, execute apenas o escopo autorizado.
Quando houver recusa, informe a necessidade de permissões/verificações e use os
canais de feedback da plataforma. Nenhum agente é obrigado a aceitar
investigações sensíveis por causa deste protocolo.

## Resultado esperado

Relatório com `REPOSITORY`, `COMMIT`, `MODE=READ_ONLY`, comandos executados
ou `NOT_RUN`, escopo, cobertura e exclusões, achados classificados como
`SUSPECTED` ou `CONFIRMED` com evidência, testes efetivamente executados e
ações sugeridas que dependem de autorização separada.

Se não houver acesso à CLI, a ferramenta não deve ser mencionada como executada.
`BOUNDED_COMPLETE` nunca equivale a pentest, verificação de RLS/GRANT de produção
ou certificação de ausência de falhas.
