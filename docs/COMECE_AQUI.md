# Comece aqui — Hybrid Engine v0.11.2

Guia para quem quer testar o Hybrid Engine público **sem precisar entender a implementação em Python**.

[Voltar à página principal](../README.md) · [Prompts prontos](EXEMPLOS_DE_COMANDOS.md) · [Protocolo](../AGENTS.md)

## 1. Antes de começar

Você precisa de:

- Um agente de IA, interface de chat, IDE ou terminal com acesso autorizado a repositórios; para criar PR, é necessária **permissão real de escrita**, não somente leitura.
- Acesso ao repositório **Hybrid Engine**. O Hybrid Engine é público, mas o projeto alvo pode exigir permissões separadas; conhecer uma URL não concede acesso a repositórios privados.
- Acesso ao **seu projeto de teste**, de preferência com baixo risco e sem dependências de produção.
- Permissão para fazer alterações no repositório alvo. Nunca use um repositório de outra pessoa sem autorização.

**Não precisa:** escolher um provedor específico, contratar GitHub Pro, copiar o framework para o projeto alvo ou habilitar GitHub Actions. Autentique-se com segurança no ambiente escolhido; nunca cole tokens em conversas.

> Se o agente não tiver acesso à leitura/escrita do GitHub, ele deve informar isso. Não interprete uma resposta inventada como execução verdadeira.

## 2. Primeiro teste em qualquer agente

1. Escolha o ambiente: **chat com ferramentas**, **agente de programação/IDE** ou **terminal**. Em chats, comece uma conversa nova; em ferramentas de código, abra o projeto.
2. Configure o acesso ao repositório e confira permissões de leitura, escrita e execução. Algumas integrações são somente leitura.
3. Peça explicitamente a leitura de `AGENTS.md` e do protocolo universal; cole o exemplo abaixo, substituindo a URL do projeto alvo.

```text
HYBRID AUTO — TESTE REAL

Framework:
https://github.com/americashowspy-create/hybrid-engine

Projeto:
https://github.com/OWNER/REPOSITORY

Leia AGENTS.md e docs/AGENT_AUTO.md da main.
Use as ferramentas e permissões realmente disponíveis neste ambiente.

1. Inspecione a branch principal e as PRs existentes.
2. Identifique UM problema comprovado, pequeno e de baixo risco.
3. Registre o diagnóstico e os arquivos/SHAs relevantes.
4. Corrija somente em uma branch isolada.
5. Execute testes locais/offline seguros quando houver ambiente.
6. Abra uma Pull Request DRAFT com evidências, riscos e rollback.
7. Apresente links e diferencie PASSED, FAILED e NOT_RUN.

Sem merge, deploy, mudanças de banco, credenciais ou produção.
Sem criar workflows ou gastar GitHub Actions desnecessariamente.
Se faltar acesso, autorização ou ambiente, explique o bloqueio real.
```

**Resultado ideal:** uma PR Draft que pode ser revisada por um humano, com logs reais de testes ou indicação transparente dos testes não executados. O objetivo não é forçar uma alteração onde não existe problema.

## 3. O que verificar na resposta

| Verificação | Evidência aceitável |
| --- | --- |
| Repositório certo | URL, branch principal e SHA reais |
| Problema verdadeiro | Arquivo/trecho e causa identificável |
| Sem retrabalho | PRs/branches existentes examinadas |
| Mudança isolada | Link da branch e da PR Draft |
| Testes reais | Comando, saída e status de cada teste |
| Limites | Riscos, pendências e rollback |
| Segurança | Confirmação de que não houve merge ou deploy |

Se o agente apenas der um parecer sem acesso de escrita comprovado, considere **auditoria/planejamento**, não execução. Se oferecer um link de PR que não abre no seu GitHub, o teste falhou.

## 3A. Primeiro contato com Codex/Claude/ChatGPT

Para uma avaliação inicial, identifique separadamente **framework** e **projeto alvo**. Comece em leitura estática e com permissões reais. Se um serviço apresentar restrições de segurança (como verificação adicional para atividades avançadas), respeite o bloqueio e solicite os motivos; **não tente contornar controles**. O Hybrid não concede acesso ao repositório, terminal ou ferramentas nem garante compatibilidade universal.

Confira se o agente realmente leu o `AGENTS.md` e executou `project-audit`; somente mencionar a URL não comprova execução. Em projetos grandes, examine `workspace` por lotes e nunca transforme `BOUNDED_COMPLETE` de arquivos em certificação de segurança.

[Guia de compatibilidade e diagnóstico de bloqueios](AGENT_COMPATIBILITY.md).

## 3B. Indicadores de cobertura (v0.11.2 publicada)

O `project-audit` informa arquivos enumerados, elegíveis, atribuídos e
pendentes sem exigir a publicação de nomes de arquivos. Em CI use
`--strict-coverage` para detectar cobertura `INCOMPLETE` pelo código de
saída 1 (o relatório continua gerado). Para manifestos de arquivos com nome,
inclua **somente quando autorizado** `--include-file-manifest` junto com
`--output` privado e fora da pasta auditada.

## 4. Escolha um modo de teste

**Só investigação (mais seguro no início)**

```text
HYBRID AUDIT
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY
Leia AGENTS.md. Faça análise somente leitura.
Liste riscos, fontes, evidências e limitações. Não altere arquivos.
```

**Erro específico**

```text
HYBRID DEBUG
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY
Problema: [descreva o erro e como reproduzir]
Investigue a causa, proponha correção mínima e testes.
Branch + PR Draft, sem merge/deploy.
```

[Mais comandos prontos](EXEMPLOS_DE_COMANDOS.md).

## 5. Posso usar pelo terminal?

Sim. Com **Python 3.11+**, clone este repositório localmente (respeitando suas permissões) e execute:

```bash
python3 -m pip install .
hybrid --version
hybrid init --target /caminho/do/projeto
hybrid inspect --target /caminho/do/projeto
hybrid run --target /caminho/do/projeto --intent "auditoria"
```

A CLI cria planos e relatórios, mas **não gera patches de IA por si só**. Para a auditoria remota, configure um `GH_TOKEN` de escopo mínimo **somente no seu ambiente local** e consulte [o guia GitHub](GITHUB_ADAPTER.md). Não envie tokens por mensagem.

Para passar fontes auditadas a um agente local, use `hybrid gh-chat-package` e `hybrid gh-execute --bundle`, descritos no [README](../README.md) e no [protocolo universal v0.9](AGENT_AUTO.md).

## 6. E se meus minutos do GitHub Actions acabaram?

O GitHub continua permitindo leitura de código, commits, branches e PRs, conforme as permissões. O bloqueio de minutos afeta a **execução hospedada de CI**.

É possível executar testes em seu computador ou num ambiente isolado com rede controlada. Porém, **Vercel Sandbox, outros serviços e sua própria infraestrutura podem ter seus próprios custos**. Não transforme o resultado offline em um check “verde” do GitHub: registre ambos separadamente.

## 7. O que não fazer

- Não execute scripts de repositórios desconhecidos sem revisão.
- Não publique bundles com fontes privadas, arquivos `.env`, chaves ou dados de clientes.
- Não autorize merge/deploy como parte automática de um teste.
- Não desative proteções de branch nem abra repositórios privados só para economizar CI.
- Não conceda acesso a projetos de terceiros quando o objetivo é testar apenas o framework.

## 8. Envie seu feedback

Após o teste, anote: **comando utilizado**, **repositório de teste (se puder divulgar)**, **resultado real**, **links de PR**, **testes executados/não executados** e **o que foi confuso**.

Se tiver acesso de colaborador ao repositório, abra uma Issue com esses detalhes. Para falhas de segurança, use divulgação privada — nunca publique credenciais ou detalhes de exploração.

[Como contribuir](../CONTRIBUTING.md) · [Segurança](SECURITY.md)
