# ⚡ Hybrid Engine

**Do pedido à Pull Request, com diagnóstico, controle de risco e evidências.**

Um framework **chat-first e independente de agente** para organizar auditorias, correções e desenvolvimento de software. Combina planejamento orientado a especificações, investigação de problemas, alterações pequenas e verificações rastreáveis — sem amarrar o fluxo ao Codex ou a um único provedor.

**Versão:** `v0.8` (experimental) · **Python:** 3.11+ (CLI opcional) · **Licença:** MIT · **Idioma:** Português / [English](docs/README_EN.md)

> [!IMPORTANT]
> O Hybrid Engine **não é um plugin nativo do ChatGPT nem uma IA própria**. É um protocolo aberto com ferramentas Python opcionais. O agente precisa ter acesso real ao código e permissão para executar cada etapa. Uma URL, sozinha, não instala ferramentas nem concede acesso.

**[Comece em 5 minutos](docs/COMECE_AQUI.md)** · **[Prompts prontos](docs/EXEMPLOS_DE_COMANDOS.md)** · **[Protocolo oficial](AGENTS.md)** · **[Segurança](docs/SECURITY.md)** · **[Contribuir](CONTRIBUTING.md)**

---

## O que o Hybrid Engine faz?

```text
Pedido no ChatGPT ou em outro agente
                 │
                 ▼
 Entender objetivo e repositório
                 │
                 ▼
 Auditar e investigar (escopo definido)
                 │
                 ▼
 Planejar a menor mudança segura
                 │
                 ▼
 Branch isolada + correção revisável
                 │
                 ▼
 Testes / evidências / limites
                 │
                 ▼
 Pull Request DRAFT + relatório + rollback
```

A ação de escrever código é feita pelo **agente conectado** (ou por um desenvolvedor). A CLI auxilia no planejamento, na auditoria, na preparação do pacote de fontes e nas validações; **não inventa correções sozinha**.

## 🚀 Experimente diretamente no ChatGPT

Não é preciso instalar Python ou Codex para seguir o protocolo **quando o ChatGPT dispõe de conexão GitHub com as permissões necessárias**.

1. Abra um chat novo e conecte a conta GitHub, conforme os recursos disponíveis na sua conta.
2. Certifique-se de que o agente pode ler o **Hybrid Engine** e o **repositório que será analisado**.
3. Cole o comando abaixo, substituindo `OWNER/REPOSITORY` pelo seu projeto.

```text
HYBRID AUTO — v0.8

Framework:
https://github.com/americashowspy-create/hybrid-engine

Projeto:
https://github.com/OWNER/REPOSITORY

Leia o AGENTS.md e docs/CHATGPT_AUTO.md do framework
e as instruções do repositório alvo.

Audite, identifique um problema real e de baixo risco, verifique se já
existe correção em andamento e proponha a menor solução possível.
Com autorização e ferramentas disponíveis, implemente em branch isolada,
execute testes offline seguros e abra uma Pull Request em Draft.

Documente diagnóstico, arquivos alterados, comandos/testes realmente
executados, resultados, riscos e rollback.
Não faça merge, deploy, migrações ou mudanças em dados/credenciais de produção.
Não dispare GitHub Actions desnecessariamente e não declare testes não
executados como aprovados.
```

**Entrega esperada:** link da PR (se autorizada e tecnicamente possível), diagnóstico, commit/arquivos envolvidos, evidências e pendências. Se faltar acesso, ferramenta ou ambiente, o resultado correto é **explicar o bloqueio**, não inventar uma PR.

➡️ Veja o passo a passo em [Comece aqui](docs/COMECE_AQUI.md) e as variações de comando em [Exemplos](docs/EXEMPLOS_DE_COMANDOS.md).

## ✨ Funcionalidades disponíveis na v0.8

| Recurso | O que entrega |
| --- | --- |
| **HYBRID AUTO** | Protocolo que direciona auditoria, investigação, correção ou planejamento conforme o objetivo. |
| **AUDIT / AUDIT-FIX / DEBUG / BUILD / REVIEW / STATUS** | Fluxos específicos para análise, correção, criação, revisão e continuidade. |
| **Auditoria estática** | Sinais heurísticos de segurança/qualidade, relatados com escopo e limitações. |
| **Planos e relatórios** | Estado local em `.hybrid/`, plano estruturado e evidências documentadas. |
| **Escopo exato e SHA** | Work orders vinculadas ao commit e aos arquivos auditados; rejeição de alterações fora do escopo. |
| **Pacote para agente** | `gh-chat-package` exporta código auditado em arquivo privado, para um agente autorizado. |
| **Prévia e PR Draft** | `gh-execute` valida um manifesto; `--apply` autoriza somente branch nova e PR Draft. |
| **Verificação de CI** | `gh-verify` consulta checks reais do HEAD da PR; não dispara testes nem inventa aprovação. |
| **Acompanhamento opcional** | `gh-task` usa GitHub Issues como diário da tarefa, com alterações explícitas. |
| **Adaptador agnóstico** | `gh-agent` suporta um executável local confiável via protocolo JSON/stdio. |

**Limites importantes:** o scanner **não é pentest**; uma auditoria ampla pode parar no limite de 250 arquivos; o fluxo por pacote usa até 20 arquivos exatos (até 64 KiB por fonte). Correções arbitrárias exigem um agente com capacidade de editar código. Não há merge, deploy ou acesso à produção automáticos.

## 🧭 Escolha o comando certo

| Comando | Quando usar |
| --- | --- |
| `HYBRID AUTO` | “Analise e decida a abordagem adequada.” |
| `HYBRID AUDIT` | “Quero entender problemas e riscos, sem alterar código.” |
| `HYBRID AUDIT-FIX` | “Investigue e corrija algo comprovado, com controles.” |
| `HYBRID DEBUG` | “Tenho um erro específico para reproduzir e corrigir.” |
| `HYBRID BUILD` | “Quero desenvolver uma funcionalidade com critérios de aceite.” |
| `HYBRID REVIEW` | “Revise um conjunto de mudanças ou uma PR.” |
| `HYBRID STATUS` | “Retome uma tarefa a partir de estado/evidências disponíveis.” |

Todos são **instruções de workflow para um agente**, não comandos oficiais embutidos no ChatGPT.

## 💻 Uso opcional pelo terminal

A CLI é feita em Python, usa apenas a biblioteca padrão em tempo de execução e não requer assinatura de modelo. Na raiz de um clone do repositório:

```bash
python3 -m pip install .
hybrid --version
hybrid init --target /caminho/do/projeto
hybrid inspect --target /caminho/do/projeto
hybrid run --target /caminho/do/projeto --intent "audite este projeto"
hybrid status --target /caminho/do/projeto
```

`hybrid run` **planeja e audita**; só tenta executar testes existentes com `--tests` (revise esses scripts antes, pois podem ter efeitos colaterais). Ele **não edita código automaticamente**.

Operações remotas via GitHub:

```bash
# Auditoria remota, sem alteração no GitHub:
hybrid gh-audit --repo OWNER/REPOSITORY --ref main

# Ordem de trabalho e pacote de código, limitados a arquivo específico:
hybrid gh-chat-package --repo OWNER/REPOSITORY \
  --goal "HYBRID DEBUG: corrigir erro" \
  --path src/app.py --output /tmp/hybrid-chat.json

# Conferir manifesto preparado por um agente (somente preview):
hybrid gh-execute --bundle /tmp/hybrid-chat.json \
  --manifest /tmp/reviewed-change.json

# Se expressamente autorizado, adicionar --apply cria APENAS uma PR Draft.
```

O arquivo `reviewed-change.json` **não é gerado automaticamente pela CLI**: deve conter as alterações preparadas e revisadas por um agente ou desenvolvedor. Para repositórios privados, a CLI usa um token GitHub de escopo mínimo (`GH_TOKEN`); no ChatGPT conectado, o acesso é realizado pelas ferramentas da própria conexão, quando disponíveis. [Guia técnico do adaptador](docs/GITHUB_ADAPTER.md).

## 🔒 Segurança, privacidade e custos

- **Sem ações silenciosas de alto impacto:** mudanças em produção, migrações, credenciais, merge e deploy exigem autorização separada.
- **Mudanças rastreáveis:** branch isolada, validação de SHAs, PR Draft e instrução de rollback.
- **Resultados honestos:** `PASSED`, `FAILED` e `NOT_RUN` têm significados distintos; check ausente não é aprovação.
- **Código privado:** confirme quem terá acesso aos arquivos antes de usar provedores/agentes externos; não compartilhe tokens nem bundles em issues ou logs.
- **Custo controlado:** testes locais não usam minutos de runners hospedados pelo GitHub, mas outros ambientes (por exemplo, sandboxes) **podem consumir franquia ou gerar cobrança própria**.

Leia as [regras de segurança](docs/SECURITY.md) e o [protocolo completo de ChatGPT](docs/CHATGPT_AUTO.md).

## 🧪 Qualidade e estado do projeto

A v0.8 teve **124 testes Python aprovados em execução offline isolada**, incluindo quatro casos de ponta a ponta com um **GitHub simulado**; os 33 arquivos Python foram comparados ao commit testado via Git blob SHA. Essa evidência está registrada na [PR #9](https://github.com/americashowspy-create/hybrid-engine/pull/9).

**O que isso comprova:** funcionamento da suíte e das simulações naquele commit. **O que não comprova:** que todo projeto de terceiros funcionará, que um agente externo terá acesso ou que o CI hospedado passou. Um piloto em repositório externo deve ser avaliado separadamente.

Para contribuir ou validar localmente:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q hybrid_engine tests
python3 -m hybrid_engine --help
```

## 🤝 Quer testar com amigos?

O projeto está **privado neste momento**. Pessoas convidadas ao repositório podem ler a documentação e testar em seus **próprios projetos**, com suas próprias permissões GitHub. Dar acesso ao framework **não exige** dar acesso aos outros repositórios do proprietário.

Comece por [Comece aqui](docs/COMECE_AQUI.md), veja os [prompts prontos](docs/EXEMPLOS_DE_COMANDOS.md) e envie feedback seguindo [Como contribuir](CONTRIBUTING.md). Não compartilhe projetos privados com terceiros sem autorização dos responsáveis.

## 📚 Documentação

- [Comece aqui — primeiros passos e beta](docs/COMECE_AQUI.md)
- [Exemplos de comandos para copiar](docs/EXEMPLOS_DE_COMANDOS.md)
- [Protocolo portátil do agente](AGENTS.md)
- [HYBRID AUTO no ChatGPT](docs/CHATGPT_AUTO.md)
- [Arquitetura](docs/ARCHITECTURE.md) · [Workflows](docs/WORKFLOWS.md)
- [Adaptador GitHub](docs/GITHUB_ADAPTER.md) · [Executor universal](docs/UNIVERSAL_EXECUTOR.md)
- [Auditoria com escopo](docs/SCOPED_AUDIT.md) · [Verificação e evidências](docs/TASK_JOURNAL.md)
- [Segurança](docs/SECURITY.md) · [Agradecimentos](ACKNOWLEDGEMENTS.md)
- [English overview](docs/README_EN.md)

---

**Projeto independente**, inspirado em conceitos do [GitHub Spec Kit](https://github.com/github/spec-kit) e [Superpowers](https://github.com/obra/superpowers). Não é fork, integração oficial ou produto afiliado a esses projetos.

Licenciado sob [MIT](LICENSE) · **v0.8 experimental** · Criado para ajudar agentes e pessoas a desenvolver software com menos improviso e mais evidências.
