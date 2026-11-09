# ⚡ Hybrid Engine

**Do pedido à Pull Request, com diagnóstico, controle de risco e evidências.**

Um framework **independente de agente, modelo e interface** para organizar auditorias, correções e desenvolvimento de software. Reúne, em componentes próprios, **planejamento orientado a objetivos, investigação de problemas, revisão de mudanças, seleção de fluxos, testes e evidências** — sem exigir um fornecedor específico.

**Versão:** `v0.8` (experimental) · **Python:** 3.11+ (CLI opcional) · **Licença:** MIT · **Idioma:** Português / [English](docs/README_EN.md)

> [!IMPORTANT]
> O Hybrid Engine **não é uma IA própria nem um plugin nativo de uma plataforma**. É um protocolo portátil com ferramentas Python opcionais. O agente escolhido precisa de acesso real ao código, recursos de execução e autorização para cada ação. Colar uma URL não instala ferramentas nem concede acesso.

**[Comece em 5 minutos](docs/COMECE_AQUI.md)** · **[Prompts prontos](docs/EXEMPLOS_DE_COMANDOS.md)** · **[Protocolo oficial](AGENTS.md)** · **[Segurança](docs/SECURITY.md)** · **[Contribuir](CONTRIBUTING.md)**

---

## O que o Hybrid Engine faz?

```text
Pedido no agente de IA ou terminal de sua escolha
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

## 🚀 Comece no ambiente de sua preferência

O protocolo pode ser seguido por **chats com acesso a repositórios, agentes de programação, ferramentas de IDE e executores locais**. A disponibilidade de leitura, escrita, terminal e GitHub depende das permissões reais de cada ambiente.

| Ambiente | Como iniciar | Requisito para alterar código |
| --- | --- | --- |
| **Chat com ferramentas** | Abra uma conversa e permita o acesso ao framework e ao projeto. | A conexão precisa oferecer **escrita**, não somente leitura. |
| **Agente de programação / IDE** | Abra o projeto localmente ou conecte o repositório e peça a leitura de `AGENTS.md`. | O agente precisa de acesso autorizado ao código, Git e ferramentas de execução. |
| **Terminal / automação** | Utilize a CLI Python opcional e um agente confiável, se necessário. | A CLI valida e organiza propostas, mas não gera patches arbitrários sozinha. |

**Comando universal para copiar:**

```text
HYBRID AUTO — v0.8

Framework:
https://github.com/americashowspy-create/hybrid-engine

Projeto:
https://github.com/OWNER/REPOSITORY

Leia AGENTS.md e docs/AGENT_AUTO.md na branch main do framework
e as instruções do projeto alvo.

Inspecione a branch principal, o SHA atual e as PRs existentes.
Identifique UM problema real e de baixo risco, investigue a causa e
proponha a menor correção segura. Se autorizado e tecnicamente possível,
implemente em uma branch isolada, execute testes seguros e abra PR Draft.

Entregue diagnóstico, arquivos/SHAs, comandos e resultados de testes,
riscos, limitações, links reais e rollback. Informe qualquer bloqueio
de acesso ou ferramenta sem inventar ações ou evidências.

Não faça merge, deploy, migrações nem alterações em produção.
Não dispare verificações hospedadas desnecessariamente.
```

**Importante:** compreender o protocolo é diferente de conseguir executá-lo. Sem ferramentas de escrita, o resultado correto é auditoria e proposta — **não uma PR inventada**.

➡️ [Comece aqui](docs/COMECE_AQUI.md) · [Comandos prontos](docs/EXEMPLOS_DE_COMANDOS.md) · [Protocolo universal](docs/AGENT_AUTO.md).

## ✨ Funcionalidades disponíveis na v0.8

| Recurso | O que entrega |
| --- | --- |
| **Roteamento inteligente de tarefas** | HYBRID AUTO direciona a auditoria, investigação, correção ou planejamento conforme o objetivo. |
| **Planejamento e especificação** | Fluxos AUDIT / AUDIT-FIX / DEBUG / BUILD / REVIEW / STATUS, com critérios de aceite e entregas verificáveis. |
| **Investigação e revisão** | Análise da causa de problemas, inspeção estática, revisão de mudanças e identificação de riscos com escopo explícito. |
| **Organização e continuidade** | Estado local em `.hybrid/`, plano estruturado e evidências documentadas para retomar o trabalho. |
| **Escopo exato e SHA** | Work orders vinculadas ao commit e aos arquivos auditados; rejeição de alterações fora do escopo. |
| **Pacote para agente** | `gh-chat-package` exporta código auditado em arquivo privado, para um agente autorizado. |
| **Prévia e PR Draft** | `gh-execute` valida um manifesto; `--apply` autoriza somente branch nova e PR Draft. |
| **Verificação de CI** | `gh-verify` consulta checks reais do HEAD da PR; não dispara testes nem inventa aprovação. |
| **Acompanhamento opcional** | `gh-task` usa GitHub Issues como diário da tarefa, com alterações explícitas. |
| **Adaptador agnóstico** | `gh-agent` suporta um executável local confiável via JSON/stdio; pode aproveitar habilidades do agente escolhido, mas **não inclui catálogo nativo de skills**. |

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

Todos são **instruções portáteis de workflow**, não comandos nativos garantidos em uma plataforma específica.

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

O arquivo `reviewed-change.json` **não é gerado automaticamente pela CLI**: deve conter as alterações preparadas e revisadas por um agente ou desenvolvedor. Para repositórios privados, a CLI usa um token GitHub de escopo mínimo (`GH_TOKEN`); num ambiente conectado, o acesso é realizado pelas ferramentas efetivamente disponíveis, quando autorizadas. [Guia técnico do adaptador](docs/GITHUB_ADAPTER.md).

## 🔒 Segurança, privacidade e custos

- **Sem ações silenciosas de alto impacto:** mudanças em produção, migrações, credenciais, merge e deploy exigem autorização separada.
- **Mudanças rastreáveis:** branch isolada, validação de SHAs, PR Draft e instrução de rollback.
- **Resultados honestos:** `PASSED`, `FAILED` e `NOT_RUN` têm significados distintos; check ausente não é aprovação.
- **Código privado:** confirme quem terá acesso aos arquivos antes de usar provedores/agentes externos; não compartilhe tokens nem bundles em issues ou logs.
- **Custo controlado:** testes locais não usam minutos de runners hospedados pelo GitHub, mas outros ambientes (por exemplo, sandboxes) **podem consumir franquia ou gerar cobrança própria**.

Leia as [regras de segurança](docs/SECURITY.md) e o [protocolo universal para agentes](docs/AGENT_AUTO.md).

## 🧪 Qualidade e estado do projeto

A v0.8 teve **124 testes Python aprovados em execução offline isolada**, incluindo quatro casos de ponta a ponta com um **GitHub simulado**; os 33 arquivos Python foram comparados ao commit testado via Git blob SHA. Essa evidência está registrada na [PR #9](https://github.com/americashowspy-create/hybrid-engine/pull/9).

**O que isso comprova:** funcionamento da suíte e das simulações naquele commit. O framework implementa seus próprios fluxos de planejamento, diagnóstico e validação; **não incorpora integralmente o código de ferramentas externas**. **O que não comprova:** que todo projeto de terceiros funcionará, que um agente externo terá acesso ou que o CI hospedado passou. Um piloto em repositório externo deve ser avaliado separadamente.

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
- [HYBRID AUTO — qualquer agente](docs/AGENT_AUTO.md) · [Guia específico para chat](docs/CHATGPT_AUTO.md)
- [Arquitetura](docs/ARCHITECTURE.md) · [Workflows](docs/WORKFLOWS.md)
- [Adaptador GitHub](docs/GITHUB_ADAPTER.md) · [Executor universal](docs/UNIVERSAL_EXECUTOR.md)
- [Auditoria com escopo](docs/SCOPED_AUDIT.md) · [Verificação e evidências](docs/TASK_JOURNAL.md)
- [Segurança](docs/SECURITY.md) · [Agradecimentos](ACKNOWLEDGEMENTS.md)
- [English overview](docs/README_EN.md)

---

**Projeto independente:** combina, em implementação própria, planejamento, investigação, revisão, controle de mudanças e evidências. Não é fork nem integração oficial de ferramentas externas. Referências e créditos técnicos: [Agradecimentos](ACKNOWLEDGEMENTS.md).

Licenciado sob [MIT](LICENSE) · **v0.8 experimental** · Criado para ajudar agentes e pessoas a desenvolver software com menos improviso e mais evidências.
