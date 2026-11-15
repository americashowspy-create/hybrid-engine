# Plano único e evidências — missão avançada

## Estado atual

Base desta missão: `8bd78e6f096584035ac67f631244446ee44963fb`.
Branch autorizada: `feat/assessment-advisor-hardening`, mesma origem privada.
Working tree inicial limpa e branch sincronizada; baseline 178 PASS reexecutada
em Python 3.11.18 e 3.12.14 (3.12 em worktree detached da base).
AGENTS, arquitetura, assessment, plano, DB Guard, workflows e segurança relidos;
Issues #13/#14 e roadmap da branch separada consultados novamente.

| Frente | Entrega e critério verificado |
| --- | --- |
| A | Enumeração compartilhada limitada por entradas/diretórios/profundidade, razões e contagens, sem contagem posterior da árvore; testes adversariais |
| B | Grafo local Python/JS/TS, SCCs, métricas de controle/fan-out, evidências no assessment e ordens no Advisor; sem alegações semânticas não demonstradas |
| C | npm/pnpm/Yarn/Bun, workspace owner/lockfile herdado, manifests independentes, conflitos e incertezas explícitas |
| D | Contrato JSON v1 + SARIF 2.1.0 restrito offline, proveniência/dedup/divergência, texto livre omitido, Advisor bloqueado para revisão independente |
| E | Cache limitado por assessment, mesmas regras/resultados com/sem cache, redução de leituras medida |

Primeiras versões funcionais das cinco frentes concluídas; cobertura semântica
ampla e adaptadores externos continuam pendentes. Contratos em ASSESSMENT.md.

## Validação final

- 229/229 PASS em Python 3.11.18 e 3.12.14, zero falhas; +51 testes sobre a base.
- compileall hybrid_engine tests PASS em ambas as versões; git diff --check PASS.
- CLI --help, assess JSON/Markdown, evidence-import JSON/Markdown e
  evidence-import → advise executados; fixtures sintéticos versionados em tests/fixtures/evidence.
- Relatórios de assessment do mesmo Hybrid e importação das mesmas fixtures
  idênticos em Python 3.11/3.12. Não garante equivalência para sintaxe exclusiva de 3.12.
- CI hospedado CI_NOT_VERIFIED; testes de produção, ferramentas externas e pentest NOT_RUN.
- Mensagem argparse de combinação inválida de --bundle/--order pertence a teste
  negativo existente e não é uma falha da suíte.

Comparação com scanner da base 8bd78e6 sobre os mesmos checkouts:

| Piloto | Antes | Depois | Cobertura |
| --- | --- | --- | --- |
| Hybrid (árvore desenvolvida) | 7 | 12 | BOUNDED_COMPLETE |
| Radar | 12 | 12 | BOUNDED_COMPLETE |

Hybrid preservou 5 SUPABASE_SECRET e 2 PUBLIC_PRIVILEGED_CONFIG em testes.
Adicionou CONCENTRATED_CONTROL_FLOW em assessment/evidence_bridge/github_adapter/
taskboard e HIGH_LOCAL_FAN_OUT na CLI (16 dependências locais). São indicadores,
incluindo o próprio código novo, não vulnerabilidades ou defeitos comprovados.
Radar preservou 6 suspeitas SQL, 1 lockfile, 1 sink HTML, 3 fontes longas e 1
indicador de testes ausentes. Não foram suprimidos alertas. HEAD do Radar continua
68c0069b0008e4829ce06011acdd91190057b839 e working tree limpa.
Relatórios detalhados e medições permanecem em work/evidence, sem publicar
metadados dos pilotos fora de seu escopo autorizado.

## Commits desta missão e publicação

1. 57c4b88 — orçamento global compartilhado.
2. e1ff224 — evidência estrutural/imports e Advisor.
3. 00466a2 — gerenciadores de pacotes/workspaces.
4. 27019ce — Evidence Bridge e JSON estrito compartilhado.
5. cc5ab19 — cache limitado e medição.
6. cfd78e8 — arquivos gerados e entradas ambíguas.
7. d199eb7 — remover falso autociclo implícito em inicializadores de pacote.
8. 3458d8d — proveniência de regra e distinção de snapshots/escopos no Advisor.
9. Commit desta atualização — documentação final e evidências.

Antes de publicar, fetch e inspeção confirmaram apenas ci.yml nos workflows,
com push main e PR para main; nenhum workflow alterado. Consulta confirmou nenhuma
PR aberta para a branch. Push autorizado somente para a branch existente, sem
force push, abertura de PR ou merge. HEAD publicado é confirmado no relatório
final de entrega e na referência remota, sem inventar SHA dentro deste commit.

## Decisões, riscos e continuidade

Sem dependências runtime novas: AST/JSON/SCC usam biblioteca padrão. Não há
exigência de Docker, Codex, modelo pago ou scanners instalados. Assessment v1
recebeu campos aditivos; o planejador e os controles de execução foram reutilizados.
Foi corrigida uma falsa dependência de inicializador de pacote consigo mesmo e
um conflito indevido no Advisor entre a mesma localização em SHAs/escopos distintos.

Próximo incremento recomendado: ampliar resolução verificável de imports
(layouts src e aliases configurados) e semântica de globs de workspace, mantendo
casos não suportados explícitos. Depois, adaptadores externos opcionais com
proveniência autenticada/revisada; sem promoção automática de confiança.

Limitações deliberadas: JS lexical não é parser completo; contagens não provam
responsabilidades de negócio ou má arquitetura; YAML limitado; SARIF não aceita
muitos recursos avançados. Claims SHA são comparados, não autenticados; metadados
podem conter segredos não reconhecíveis; revisão de relatórios segue necessária.
Enumeração não tem timeout de syscalls e cache não fornece snapshot atômico.
Detalhes e limites de recursos em ASSESSMENT.md.

Main/produção/Radar/banco sem alterações. Sem migrations, rotação, deploy, release,
pentest, instalação de scanners, CI hospedado solicitado ou serviços pagos.
Rollback: abandonar a branch para voltar à main; se incorporada mediante revisão
separada, reverter commits desta missão na ordem inversa, sem alterações de dados.

---

## Histórico da missão anterior (até 8bd78e6)

As pendências e estados abaixo registram a execução anterior; o estado atual e
os resultados da nova missão estão acima. Há um único plano, sem tracker paralelo.


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

Fase B: camada estrutural funcional (`structure.py`) usa AST Python padrão e um
subconjunto lexical de imports/export de JS/TS, sem executar módulos. Grafo de
arquivos locais, fan-in/out, componentes fortemente conectados e contagens de
controle/definições alimentam findings e Advisor existentes. Limites: 128 KiB por
fonte, 50000 nós AST globais e 2000 arestas; falhas/limites => INCOMPLETE.
Sem inferir responsabilidades de negócio a partir de nomes ou afirmar arquitetura
ruim por contagens. JS dinâmico, aliases de bundler e layout src Python não resolvidos.
Primeira validação: 197 testes PASS; piloto Hybrid adicionou 4 indicadores de
controle concentrado e 1 fan-out; Radar manteve os 12 achados. Análises são pistas.

Fase C: `packages.py` analisa até 100 manifests de 64 KiB, sem instalações.
Identifica npm/pnpm/Yarn/Bun, packageManager, lockfiles locais e herdados em
workspaces, múltiplos manifests independentes, conflitos e incompatibilidades.
Subconjunto pnpm YAML restrito a lista packages; padrões de exclusão/anchors e
managers desconhecidos exigem revisão e cobertura incompleta. Ausência de lock
em workspace é reportada no proprietário, evitando duplicatas nos filhos.
Validação incremental: 203 testes PASS em Python 3.12; gates 3.11 no fechamento.

Fase D: Evidence Bridge offline funcional, contrato `external_evidence` v1 e
subconjunto SARIF 2.1.0. `evidence-import --report` normaliza para assessment v1,
reutiliza Advisor e bloqueia implementação até revisão independente. Até 8 arquivos
JSON de 8 MiB e 2000 resultados globais, profundidade 64; parser estrito compartilhado
com Advisor e manifests. Proveniência por ferramenta/versão/digest/claim SHA/ambiente.
SHA esperado é comparação de alegações, nunca autenticação do código.
Mensagens livres/snippets/comandos omitidos por completo; metadados sensíveis
reconhecíveis rejeitados. Dedup apenas por mapeamento explícito + local/escopo/SHA;
severidades/claims divergentes preservados, confiança sempre suspected. SARIF sem
escopo exato ou execução bem-sucedida declarada é INCOMPLETE. URIs remotas,
base URIs, índices de artefatos e suppressions não são suportados; nada é buscado.
Validação D: 220 testes PASS; fixtures sintéticos, sem instalar ou executar ferramentas.

Fase E: cache de bytes por assessment limitado a 8 MiB, sem persistência. Mantém
os limites menores de cada consumidor, não armazena falhas e não cruza raízes.
Teste compara relatório com cache habilitado/desabilitado (exceto métricas), sem
mudanças em achados/cobertura. Fixture de uma fonte passa de 4 para 1 leitura física.
Medição local, Python 3.12.14, mediana de 7 assessments do mesmo snapshot:

| Piloto | Leituras sem/com cache | Mediana sem/com cache |
| --- | --- | --- |
| Hybrid | 210 / 54 | 145,902 / 133,534 ms |
| Radar | 124 / 35 | 51,791 / 50,071 ms |

Contagens são evidência do trabalho de IO evitado, tempos são apenas observações
neste ambiente, não benchmark universal. Cache byte-only evita duplicar AST/textos.
Gates E: 224 testes PASS em Python 3.11.18 e 3.12.14.
