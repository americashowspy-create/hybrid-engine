# ⚡ Hybrid Engine

**Do pedido à análise. Da análise à mudança revisável — com evidências, limites e controle humano.**

O **Hybrid Engine** é um framework público e independente de fornecedor para orientar agentes de IA no diagnóstico, na revisão e na evolução de software. Combina um **protocolo portátil** (Codex, Claude Code, ChatGPT com ferramentas, IDEs e outros) com uma **CLI Python opcional** de análise estática e integração controlada com GitHub.

**Versão atual: `0.11.2`** · Branch `main` · Python **3.11+** · Licença [MIT](LICENSE) · Repositório **público** · [English](docs/README_EN.md)

> **Importante:** o Hybrid **não é um modelo de IA**, não é plugin nativo, não substitui o raciocínio do agente e não concede automaticamente acesso a código ou sistemas. Um agente precisa de **ferramentas e permissões reais**. Auditorias amplas são **somente leitura por padrão**; correções, PRs, merges e deploys exigem autorização apropriada.

[Comece aqui](#-comece-em-3-passos) · [Recursos](#-o-que-já-funciona) · [Terminal](#-uso-pelo-terminal) · [Evidências](#-validação-e-evidências) · [Prompts prontos](docs/EXEMPLOS_DE_COMANDOS.md) · [Protocolo dos agentes](AGENTS.md) · [English](docs/README_EN.md)

---

## 🎯 Qual problema resolve?

Pedidos como “audite meu sistema” ou “corrija meu projeto” podem produzir confusão: **qual é o projeto-alvo? qual commit foi examinado? o que realmente rodou? quais riscos estão comprovados? há autorização para alterar código?**

O Hybrid organiza a resposta em etapas auditáveis:

~~~text
Solicitação do usuário
         ↓
Identificar projeto-ALVO, branch, SHA e permissões
         ↓
Inspecionar e registrar escopo, evidências e limitações
         ↓
Propor correções em ordem de prioridade
         ↓
[AUTORIZAÇÃO SEPARADA] agente implementa mudança mínima
         ↓
Branch isolada + testes reais + PR Draft
         ↓
Revisão humana; merge/deploy somente quando autorizados
~~~

**O repositório do Hybrid Engine é a ferramenta. O projeto informado pelo usuário é o alvo.** Não confundir os dois faz parte do protocolo. A ferramenta não promete que uma IA entendeu perfeitamente um pedido: exige que o agente **declare sua interpretação e as evidências**.

## 🚀 Comece em 3 passos

### 1. Escolha um projeto sob seu controle

Abra um repositório num agente que realmente possa acessá-lo (por exemplo, Codex, Claude Code, ChatGPT conectado ao GitHub ou uma IDE). Se você informar **apenas um site público**, o agente poderá avaliar somente o que estiver publicamente acessível e permitido; não poderá afirmar ter examinado código, banco ou fluxos internos.

### 2. Copie este prompt para a primeira análise

~~~text
Quero utilizar o Hybrid Engine:
https://github.com/americashowspy-create/hybrid-engine

PROJETO-ALVO: https://github.com/OWNER/REPOSITORY

Leia AGENTS.md e docs/PROJECT_AUDIT.md do Hybrid.
Identifique e confirme qual projeto, branch e commit você pode acessar.
Analise arquitetura, qualidade, dependências, dados, confiabilidade
e riscos defensivos, de acordo com as ferramentas realmente disponíveis.

Se houver checkout local e Python 3.11+, execute project-audit e
informe a versão, os comandos executados, a cobertura e os limites.
Caso não consiga executar algo, marque NOT_RUN ou NOT_VERIFIED.
Diferencie achados comprovados de suspeitas; não invente resultados.

Quero apenas o diagnóstico e uma lista priorizada de melhorias.
Não altere código, banco, credenciais, infraestrutura ou produção;
não faça commits, PRs, merges, deploys ou testes invasivos.
~~~

Substitua `OWNER/REPOSITORY` pelo **seu** projeto, não pelo próprio Hybrid. Depois do diagnóstico, selecione quais melhorias deseja autorizar.

### 3. Verifique o resultado

Peça **SHA real, arquivos e linhas relevantes, cobertura, comandos e saídas**, além de resultados `PASSED` / `FAILED` / `NOT_RUN`. Um deploy `READY` ou uma IA afirmando que “usou o Hybrid” **não comprova** que as ferramentas foram executadas.

[Guia para iniciantes](docs/COMECE_AQUI.md) · [Prompt genérico para sites e repositórios](docs/AGENT_COMPATIBILITY.md) · [Exemplos de tarefas](docs/EXEMPLOS_DE_COMANDOS.md).

## ✨ O que já funciona

| Recurso | O que entrega |
| --- | --- |
| **`project-audit`** | Relatório JSON somente leitura combinando Assessment e Advisor; não executa scripts do projeto-alvo. |
| **Auditoria automática de projetos grandes (v0.11.1)** | Segunda análise em lotes **exatos de até 250 arquivos**, até **16 lotes / 4.000 arquivos elegíveis atribuídos**, quando a primeira leitura alcança o teto. |
| **Resumo de cobertura (v0.11.2)** | `coverage_summary` informa arquivos enumerados, elegíveis, atribuídos, pendentes, descartados e contagens efetivamente examinadas pelos scanners. |
| **Cobertura estrita para CI (v0.11.2)** | `--strict-coverage` retorna **1** se a cobertura estática efetiva ficar `INCOMPLETE`, ainda gravando o relatório; **0 não certifica segurança**. |
| **Manifesto opcional (v0.11.2)** | `--include-file-manifest` lista caminhos relativos por lote e pendências com opt-in, até **4.096 nomes**, exigindo saída fora do projeto. |
| **Audit Intelligence / DB Guard** | Heurísticas estáticas de código, imports locais, estrutura, workspaces, configurações e indícios de problemas SQL/RLS. |
| **Implementation Advisor** | `advise` transforma achados em ordens de revisão e prioridades, sem aplicar patches por conta própria. |
| **Evidence Bridge** | `evidence-import` recebe evidências JSON/SARIF dentro de limites e mantém informações de origem. |
| **Protocolos para agentes** | Fluxos `AUTO`, `AUDIT`, `AUDIT-FIX`, `DEBUG`, `BUILD`, `REVIEW` e `STATUS`. |
| **GitHub com permissão** | Ferramentas `gh-audit`, `gh-workorder`, `gh-chat-package`, `gh-advice-package`, `gh-execute`, `gh-verify`, `gh-task` e outras. Branch e PR Draft apenas nos fluxos compatíveis e com autorização explícita. |
| **Rastreabilidade** | Registro de cobertura, limites, resultados de testes, evidências, SHAs, propostas e caminhos de rollback. |

A CLI local usa **biblioteca padrão Python em tempo de execução**; não consome uma API de IA por si só. Custos de agentes, runners ou plataformas externas são separados.

## 🔍 Como interpretar a auditoria

A versão 0.11.2 mantém a primeira leitura em `assessment` e as recomendações iniciais em `advisor`. Quando o limite de arquivos exige lotes, inclui `workspace`; o resumo `coverage_summary` indica o estado **efetivo** da cobertura.

- **`enumerated_regular_files`**: arquivos regulares encontrados, inclusive os não elegíveis.
- **`eligible_files`**: arquivos elegíveis segundo os tipos, tamanhos e limites suportados.
- **`assigned_files` / `unassigned_files`**: arquivos atribuídos à leitura por lotes ou que ficaram pendentes. Na opção `--no-auto-scope`, referem-se à seleção da primeira passagem.
- **`general_files_scanned` / `db_files_scanned`**: contagens próprias dos scanners; não representam testes funcionais, autenticação real ou segurança comprovada.
- **`BOUNDED_COMPLETE`**: conclusão do **escopo estático delimitado**, não certificação de ausência de vulnerabilidades. Relações entre lotes, comportamento em produção, backups, permissões efetivas de banco e testes da aplicação exigem verificações adicionais.
- **`INCOMPLETE`**: trabalho truncado, arquivo inacessível ou limite atingido; quantidade de arquivos não enumerados pode ser desconhecida.

O `--strict-coverage` altera **apenas o código de saída** em uma execução válida: `0` para cobertura estática efetiva concluída, `1` para incompleta e `2` para erro operacional/de argumentos. Não falha simplesmente porque encontrou achados suspeitos. Sem a opção, o comportamento de sucesso técnico permanece o anterior.

**Privacidade:** o manifesto de nomes é **desativado por padrão**. `--include-file-manifest` exige `--output` externo à árvore-alvo, lista no máximo 4.096 caminhos e registra omissões. Não inclui os conteúdos dos arquivos nem valores de `.env` privados; **os próprios nomes ainda podem ser sensíveis**, portanto não publique relatórios privados.

## 💻 Uso pelo terminal

Para executar com **Python 3.11+** a partir de um clone local:

~~~bash
git clone https://github.com/americashowspy-create/hybrid-engine.git
cd hybrid-engine
python3 -m hybrid_engine --version
python3 -m unittest discover -s tests -v
~~~

Também é possível instalar localmente com `python3 -m pip install .` para usar o comando `hybrid`.

**Auditoria padrão (leitura estática, saída fora do alvo):**

~~~bash
python3 -m hybrid_engine project-audit --target /caminho/do/projeto --output /tmp/hybrid-audit.json
~~~

**CI: cobertura incompleta deve resultar em código 1:**

~~~bash
python3 -m hybrid_engine project-audit --target /caminho/do/projeto --output /tmp/hybrid-ci.json --strict-coverage
~~~

**Manifesto privado opcional:**

~~~bash
python3 -m hybrid_engine project-audit --target /caminho/do/projeto --output /tmp/hybrid-private.json --include-file-manifest
~~~

**Comparação com a primeira leitura limitada:**

~~~bash
python3 -m hybrid_engine project-audit --target /caminho/do/projeto --output /tmp/hybrid-legacy.json --no-auto-scope
~~~

**Ferramentas adicionais:**

~~~bash
python3 -m hybrid_engine assess --target /caminho/do/projeto --output /tmp/assessment.json
python3 -m hybrid_engine advise --report /tmp/assessment.json --output /tmp/advice.json
python3 -m hybrid_engine db-audit --target /caminho/do/projeto
python3 -m hybrid_engine gh-audit --repo OWNER/REPOSITORY --ref main
python3 -m hybrid_engine gh-verify --repo OWNER/REPOSITORY --pr 123
~~~

`assess` isolado mantém seu limite próprio de 250 arquivos. `gh-audit` é uma análise **remota separada**, não equivale ao `project-audit` com checkout. Para repositórios privados, operações de GitHub podem exigir um `GH_TOKEN` com acesso mínimo. Revisar scripts do alvo antes de optar por executá-los.

[Documentação técnica](docs/ASSESSMENT.md) · [Auditoria multidimensional](docs/PROJECT_AUDIT.md) · [Adaptador GitHub](docs/GITHUB_ADAPTER.md).

## 🧭 Qual fluxo pedir ao agente?

| Pedido | Finalidade | Permissão padrão |
| --- | --- | --- |
| `HYBRID AUDIT` | Revisar sistema e propor prioridades | Somente leitura |
| `HYBRID DEBUG` | Investigar erro específico | Investigar; corrigir após autorização |
| `HYBRID AUDIT-FIX` | Corrigir achado reproduzível | Branch/PR Draft somente se autorizado |
| `HYBRID BUILD` | Implementar recurso com critérios de aceite | Mudança revisável autorizada |
| `HYBRID REVIEW` | Revisar uma PR | Somente leitura |
| `HYBRID STATUS` | Retomar uma tarefa com evidências | Somente leitura |
| `HYBRID AUTO` | Escolher o fluxo adequado ao pedido | Não concede permissões automaticamente |

Essas expressões são **convenções portáteis**, não comandos nativos de todas as plataformas.

## 🧪 Validação e evidências

A `main` pública da **v0.11.2** está no commit [`71b83204135fc2adde959149f20de2bcc98f141a`](https://github.com/americashowspy-create/hybrid-engine/commit/71b83204135fc2adde959149f20de2bcc98f141a).

- **287 testes Python aprovados** na PR [#20](https://github.com/americashowspy-create/hybrid-engine/pull/20), com CI e smoke da CLI bem-sucedidos no [GitHub Actions](https://github.com/americashowspy-create/hybrid-engine/actions/runs/44286423222).
- O **CI da própria `main`** também concluiu com sucesso após o merge, incluindo o smoke da CLI e a auditoria remota do repositório: [execução #44288317307](https://github.com/americashowspy-create/hybrid-engine/actions/runs/44288317307).
- Na **v0.11.1**, um teste independente com Codex relatou **261/261 arquivos elegíveis em dois lotes**, achado SQL após o 250º arquivo e limite honesto de **4.000/4.001 atribuídos**. Este teste externo não substitui validação específica da experiência de agentes na v0.11.2.

**O que foi validado:** suíte automatizada, comandos de CLI e execução estática por lotes em cenários controlados. **O que não foi certificado:** ausência de vulnerabilidades, segurança de produção, comportamento de todos os agentes ou qualidade de qualquer projeto externo.

[Changelog completo](CHANGELOG.md) · [Como contribuir](CONTRIBUTING.md).

## 🔒 Segurança e responsabilidade

Não envie tokens ou dados privados para prompts públicos. O framework não realiza automaticamente pentest ativo, acesso a banco real, migrações, merge ou deploy. Achados estáticos são **indícios**, e mudanças de alto impacto exigem revisão específica. Nunca reformule pedidos para contornar controles de segurança de uma plataforma.

**Para experimentar:** o repositório Hybrid é **público**; o **seu projeto-alvo** pode ser privado e requer acesso independente. Use repositórios de teste sob sua autorização. Envie problemas reproduzíveis sem segredos seguindo [CONTRIBUTING.md](CONTRIBUTING.md).

---

Documentação: [Comece aqui](docs/COMECE_AQUI.md) · [Prompts](docs/EXEMPLOS_DE_COMANDOS.md) · [Protocolo](AGENTS.md) · [Compatibilidade](docs/AGENT_COMPATIBILITY.md) · [Arquitetura](docs/ARCHITECTURE.md) · [Segurança](docs/SECURITY.md) · [English](docs/README_EN.md).

**Projeto independente e aberto, sob licença [MIT](LICENSE).** O Hybrid aplica métodos próprios de análise e organização do trabalho; não é integração oficial de fornecedores de IA.