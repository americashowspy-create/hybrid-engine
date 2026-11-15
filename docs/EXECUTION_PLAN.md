# Execução incremental — Audit Intelligence e Advisor

## Estado e contexto

Base: `eff0c137d4ddbfbe5b727c52cfe6c6db8b134827`, branch isolada
`feat/assessment-advisor-hardening`. Clone novo, working tree inicialmente limpo.
Remote: `https://github.com/americashowspy-create/hybrid-engine.git`.
Main observada: `d32f251311a091ee8ab4cc1a86092bfce0d80399`.
Issues #13/#14 e comentários consultados; nenhuma PR aberta na inspeção.
O roadmap foi lido de `origin/docs/security-validation-roadmap`, não presumido na main.

## Entregas e decisões

- A: leituras limitadas com descritores, rejeição de especiais/symlinks intermediários,
  falhas de travessia contabilizadas; contexto de testes e lockfiles refinado;
  Markdown seguro para nomes de arquivos; HTML tratado como sink a investigar;
  limite de 2000 achados no scanner geral e exclusões consistentes de artefatos.
- B: `advise --report` JSON/Markdown, offline, validação de schema e limites,
  deduplicação e rejeição de conflitos, ordens por regra com testes/aceite/rollback.
  Cobertura incompleta e regras desconhecidas bloqueiam implementação.
- C: entrega parcial de planejamento: tamanho/duplicação alimentam o Advisor usando
  `core.FLOWS['review']`; ambos os caminhos duplicados ficam preservados. Não há
  análise semântica, AST, grafo de dependências ou novo comando HYBRID REFACTOR.
- D: não iniciada. Evidence Bridge JSON/SARIF depende de decisões de contrato de
  proveniência/redação e de ampliar a análise arquitetural. Não improvisar um
  importador genérico de mensagens externas sobre este contrato restrito.

Sem dependências Python adicionais, LLM, serviços pagos ou exigência de Codex.
Reutilização do planejador existente evita gerenciadores concorrentes.
Ordens do Advisor não são manifests executáveis; precisam de SHA/base/blob atuais.
POSIX é necessário para leitura por descritores. Em outras plataformas, cobertura
fica incompleta; não há fallback silenciosamente menos seguro.

## Evidência real — 15/11/2026

| Gate | Resultado |
| --- | --- |
| Baseline original, Python 3.12.14 | 151/151 PASS |
| Baseline original, Python 3.11.18 em worktree detached | 151/151 PASS |
| Incremento A | 159/159 PASS |
| Advisor | 175/175 PASS em Python 3.11 e 3.12 |
| Final, Python 3.12.14 | 178/178 PASS |
| Final, Python 3.11.18 | 178/178 PASS |
| compileall hybrid_engine tests, ambas versões | PASS |
| git diff --check | PASS |
| CLI --help / assess JSON / advise JSON e Markdown | PASS |
| GitHub Actions | CI_NOT_VERIFIED; não solicitado |

A saída de argparse `--bundle not allowed with --order` pertence a um teste
negativo existente; a suíte termina OK. Python 3.11.18 foi instalado por uv em
`/workspace/work/python`; o link global não foi criado e não é necessário.

Pilotos executados sem carregar código dos alvos, sem scripts, rede ou banco
pelos scanners. Mesmos checkouts avaliados com scanner antigo e novo:

| Piloto | Antes | Depois | Cobertura |
| --- | --- | --- | --- |
| Hybrid Engine | 7 | 7 | BOUNDED_COMPLETE |
| Radar Artístico | 12 | 12 | BOUNDED_COMPLETE |

Hybrid: 5 SUPABASE_SECRET e 2 PUBLIC_PRIVILEGED_CONFIG, todos em testes.
Radar: 6 PERMISSIVE_SQL_POLICY, 1 MISSING_JS_LOCKFILE, 1 REACT_HTML_INJECTION,
3 LARGE_SOURCE_FILE e 1 NO_TESTS_DETECTED. Mesmas contagens por regra, sem
supressões. SQL continua suspeita; não foi verificada autorização efetiva.
Radar HEAD: `68c0069b0008e4829ce06011acdd91190057b839`; working tree limpo
antes/depois. Advisor produziu 12 ordens `REVIEW_REQUIRED`, sem aplicar mudanças.
Relatórios completos ficam na área de trabalho `work/evidence`, não publicados
por conterem metadados de projetos privados.

## Commits e publicação

- `75c927f`: leitura/cobertura e primeiras regressões.
- `75c8f90`: Advisor, CLI, documentação e testes.
- `62d2219`: evidência das duplicações e limite de achados.
- Commit seguinte: registro final desta execução e limitações.

Antes de publicar: somente `.github/workflows/ci.yml` existe na main observada;
aciona push para main e PR para main. Push de branch nova sem PR não corresponde
a esses gatilhos. Nenhum workflow foi modificado. Não abrir PR nesta missão para
evitar execução hospedada; não fazer merge nem deploy.

## Próximos incrementos

1. Orçamento global de enumeração e contagem explícita de exclusões; evitar prometer
   tempo limitado apenas com limites de tamanho/achados.
2. Tornar contexto de package manager/workspaces mais preciso e melhorar evidência
   de responsabilidades/dependências antes de ampliar System Design.
3. Elaborar contrato de proveniência e redação do Evidence Bridge com fixtures,
   preservando divergências; depois estudar SARIF. Sem executar ferramentas externas.

IDs são determinísticos por localização, não imunes a deslocamento de linhas.
Não há confirmação de exploração, RLS efetivo, custos, produção ou segurança global.

## Segurança e rollback

Produção, main, Radar e banco sem alterações. Sem migrations, rotação de credenciais,
Actions, instalação de scanners, Strix, pentest, release ou deploy.
Para abandonar, deixar de usar esta branch. Se os commits forem incorporados após
revisão separada, revertê-los em ordem inversa preserva a base; não há migração de
estado ou dados. A instalação Python isolada não altera dependências do framework.

## Nova missão — baseline 8bd78e6

Baseline reexecutada: 178 PASS em Python 3.11.18. Fase A implementada com
`enumeration.py`, compartilhada pelos scanners: 20000 entradas, 1000 diretórios,
profundidade 64. Contagem inclui entradas inelegíveis e diretórios ignorados;
sem varredura adicional para obter totais desconhecidos. Diretório parcialmente
enumerado é descartado para preservar determinismo. Uma enumeração por assessment.
Falhas e arquivos especiais tornam cobertura incompleta; symlinks e diretórios
ignorados são exclusões intencionais contabilizadas. Suíte: 188 PASS em 3.11/3.12.
Próximos ciclos: B estrutura/imports; C package managers/workspaces; D bridge offline;
E medições e redução de releituras quando justificadas.
