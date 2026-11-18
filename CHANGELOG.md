# Changelog

## [0.11.1] — candidata, pendente de validação e revisão

- `project-audit` tenta automaticamente análise offline em lotes de até 250
  arquivos exatos quando a primeira varredura trunca por limite de arquivos.
- Limite de 16 lotes, exclusão de .env privados, saídas fora da árvore do alvo,
  sem invocar scripts, SQL, redes ou operações de GitHub.
- Relatório `workspace` aditivo, com contagem de arquivos elegíveis,
  cobertura por lote, achados e ordens consolidados, limites explícitos,
  sinalização de faltas, separação do estado da varredura original.
- `--no-auto-scope` mantém o comportamento da v0.11 para comparação.
- Guia de compatibilidade Codex/ChatGPT/Claude, sem instruções para contornar
  restrições de segurança e sem alegar integração nativa.
- Documentação de onboarding e README atualizados, com histórico real da v0.11.0.
- **NÃO HOMOLOGADA:** testes locais e CI da versão 0.11.1 ainda pendentes.
  Sem merge na main e sem deploy nesta candidata.

## [0.11.0] — integrada em 2026-11-17

- Project Audit com Assessment + Advisor em modo read-only.
- Safe Handoff privado com escopo de arquivos e SHA de revisão.
- Scanner AST particionado e declaração explícita de incompletude.
- 266 testes locais aprovados na candidata final (HEAD `670f07e`).
- PR #18 integrada à main em `1289684185e48cfbefc9bea7e3f1fe4f9e2a8513`.
- CI hospedado falhou sem apresentar etapas; não declarar aprovação.

## [0.10.0] — 2026-11-17 (beta offline)

Integrado à `main` pela PR #15, após homologação local (251 testes Python 3.11 e piloto
Radar Artístico offline com 12 ordens de revisão e projeto intacto). GitHub Actions
hospedado **NOT_VERIFIED** por falha sem logs e franquia esgotada. O código foi
homologado na branch no commit `f028e8b`; alterações desta preparação são apenas
versão e documentação, sem alterar a lógica de avaliação.

### Funcionalidades integradas na versão beta

- Assessment offline unificado, Advisor determinístico e importação JSON/SARIF
  limitada de evidências externas, sem ferramentas ou modelos obrigatórios.
- Orçamentos globais de enumeração, estrutura/imports locais e package managers/
  workspaces; cache de bytes limitado por assessment.

### Consolidação pré-PR (base 8ee1285)

- Corrigida herança de workspace/lockfile: `*` não atravessa separadores; `**`
  corresponde a níveis explícitos; globs não suportados indicam cobertura incompleta.
- Corrigida omissão silenciosa de arquivos substituídos por symlinks; nomes sem
  UTF-8 produzem cobertura incompleta sem derrubar o relatório. Caminhos relativos
  acima de 1024 caracteres são excluídos com cobertura incompleta, preservando o
  contrato assess → advise.
- Resolução Python prioriza packages sobre módulos homônimos; imports relativos
  fora do package e alvos JS/TS ambíguos ficam não resolvidos, sem arestas inventadas.
- Evidence Bridge isola fontes sem SHA por arquivo/run e repositórios declarados
  distintos; Advisor rejeita confiança/origem contraditórias em evidências externas.
- Limitada expansão de escopos, quantidade global de caminhos e saída JSON
  consolidada, que deve caber no limite de entrada de 8 MiB do Advisor.
- Smoke tests offline de assessment/Advisor/Evidence Bridge preparados no workflow;
  executados apenas localmente nesta missão. GitHub Actions NOT_VERIFIED.

### Compatibilidade e limitações

- Sem novas dependências runtime, comandos ou alterações no schema_version=1.
  Campos de proveniência repository/snapshot_partition e unresolved_imports são
  aditivos. A integração preservou as funcionalidades existentes da v0.9, acrescentando os módulos beta.
- IDs de evidências com SHA conhecido e sem repositório novo preservados. Sem SHA
  ou com namespace repository explícito, a identidade muda para impedir mistura.
- Relatórios antigos sem SHA que já misturaram múltiplas fontes podem ser rejeitados
  pelo Advisor: reimporte os arquivos originais para particionamento correto.
- Globs antes aceitos por interpretação excessivamente ampla agora podem gerar
  INCOMPLETE; relatórios grandes/expansivos antes aceitos agora são rejeitados.
- Nenhuma alegação de ferramenta externa é confirmação de vulnerabilidade; revisão
  independente continua obrigatória. O tratamento macOS de pai /tmp canônico é
  preservado e symlink no arquivo final permanece bloqueado.

Evidências, resultados reais dos testes e ressalvas: docs/EXECUTION_PLAN.md.
