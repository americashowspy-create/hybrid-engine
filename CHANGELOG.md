# Changelog

## Não lançado — branch feat/assessment-advisor-hardening

A main continua em v0.9.0. Esta lista descreve desenvolvimento para revisão, não
uma release publicada ou integração já homologada.

### Funcionalidades em desenvolvimento

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
  aditivos. A main e suas funcionalidades existentes não foram modificadas.
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
