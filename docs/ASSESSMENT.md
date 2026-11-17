# Audit Intelligence, System Design e Evidence Bridge — beta offline v0.10.0

Integrado à `main` na PR #15; versão beta v0.10.0, com CI hospedado ainda não verificado.
Implementação experimental, offline e independente de agente/LLM. Não é pentest,
certificação de segurança ou verificação de comportamento em produção.

## Uso

~~~bash
python3 -m hybrid_engine assess --target /projeto --output /tmp/assessment.json
python3 -m hybrid_engine assess --target /projeto --format markdown
python3 -m hybrid_engine advise --report /tmp/assessment.json --format markdown --output /tmp/advice.md
~~~

Por padrão, assess/advise imprimem relatórios e não escrevem na árvore alvo.
`--output` pede explicitamente uma gravação; não aponta para arquivos do piloto.
Não executam código/testes/scripts, carregam .env reais, instalam dependências,
conectam a banco ou acessam rede. Comandos antigos e assessment schema v1 mantidos.
Nenhuma pasta `.hybrid/` é criada por esses comandos.

## Cobertura e limites

A enumeração compartilhada examina no máximo 20000 entradas, 1000 diretórios e
profundidade 64, incluindo entradas inelegíveis. Ignora diretórios de artefatos e
symlinks antes de descentes. A travessia é iterativa, ordenada por diretório; não
faz segunda varredura para contar o restante. Um diretório que consome o orçamento
restante é descartado inteiro para evitar um subconjunto arbitrário dependente da
ordem do filesystem. Caminhos relativos têm o mesmo limite de 1024 caracteres do leitor de relatórios;
excedentes são contabilizados em path_length_excluded e tornam cobertura incompleta.
Nomes de arquivo sem representação UTF-8 são contabilizados como falhas, sem
interromper o relatório. Arquivos regulares trocados por symlink entre inventário e
leitura contam como falha, em vez de desaparecerem silenciosamente.
Atingir exatamente o limite de entradas também é truncamento
conservador. Diretórios já completados permanecem no relatório.

`coverage.enumeration` registra limites, entradas/diretórios examinados, exclusões
intencionais, arquivos especiais, erros, entradas descartadas e motivos
`entry_budget`, `directory_budget`, `depth_budget`. Quantidade não examinada é
`null` quando desconhecida: nunca estimada por uma travessia adicional.
Falhas, especiais e truncamento tornam a cobertura incompleta. Symlinks e
diretórios de artefatos são exclusões intencionais, não evidência de segurança.
`BOUNDED_COMPLETE` significa apenas conclusão do escopo elegível delimitado.

O assessment analisa até 250 fontes elegíveis de 256 KiB, com limites independentes
do DB Guard (250 arquivos/500 achados) e scanner geral (2000 achados).
Scanners separados também usam o orçamento global. A leitura por descritores
relativos impede seguir symlinks em componentes intermediários; arquivos especiais
não são abertos para processamento. Requer POSIX com `dir_fd`/`O_NOFOLLOW`;
plataformas sem suporte ficam incompletas, sem fallback menos seguro.
Filesystem lento/remoto pode bloquear operações individuais: os orçamentos de
contagem não são timeouts, nem sandbox contra controle do processo/sistema inteiro.

Uma enumeração por assessment e cache temporário de bytes de até 8 MiB reduzem
releituras. Os limites menores de cada consumidor continuam valendo. Cache não é
persistido e não garante snapshot atômico de arquivos modificados durante o scan.
`processing` contém contagens de leituras/cache, nunca conteúdo de fontes.

## Achados e contexto

Scanner geral e DB Guard preservam severidade e confiança `suspected`.
`context=test_source|application_source` e `summary` auxiliam triagem sem descartar
possíveis segredos reais em testes. Relatórios não incluem valores correspondentes
nem snippets. Caminhos são metadados potencialmente sensíveis; revise antes de compartilhar.
Markdown escapa nomes de arquivos. IDs por origem/regra/caminho/linha são estáveis
no mesmo snapshot, mas não permanecem iguais após deslocamentos de linhas.

`REACT_HTML_INJECTION` é uma pista de sink HTML: pede rastrear origem/interpolação/
sanitização. HTML estático confiável pode dispensar correção. A análise não comprova
exploração nem valida sanitizadores. Policies SQL abertas seguem suspeitas: papéis,
GRANT, finalidade e isolamento efetivo exigem verificação separada autorizada.

## System Design Intelligence

`structure` apresenta arquivos analisados, método, definições, ramificações, fan-in/
fan-out local, arestas de imports, exclusões de código gerado e lacunas. Python usa
AST da biblioteca padrão sem importar o alvo. JS/TS usa um subconjunto lexical de
import/export estático relativo, descartando comentários, strings e templates.

- `LOCAL_IMPORT_CYCLE`: componente fortemente conectado no grafo observado, com
  arquivos envolvidos e contagem; pode ser intencional e exige revisão.
- `HIGH_LOCAL_FAN_OUT`: pelo menos dez dependências locais resolvidas; uma composição
  central pode ser correta, não se deve fragmentá-la automaticamente.
- `CONCENTRATED_CONTROL_FLOW`: pelo menos trinta ramificações em cinco definições
  Python; não é um score de qualidade ou uma inferência de responsabilidade de negócio.
- `LARGE_SOURCE_FILE`: mais de 500 linhas, contextual e sem conclusão automática.
- `EXACT_DUPLICATE_SOURCE`: igualdade de bytes em fontes de pelo menos 1024 bytes;
  `related_paths` preserva o outro arquivo, sem assumir que consolidar seja desejável.
- `NO_TESTS_DETECTED`: ausência de nomes convencionais no escopo, nunca prova de
  ausência de estratégia de testes. JSON `test_*` não equivale a teste executável.

Limites estruturais: 128 KiB por fonte, 50000 nós AST globais, 2000 arestas.
Parsing/limites/leitura impossíveis são registrados e tornam assessment incompleto.
Pacotes Python com `__init__.py` têm precedência sobre módulos `.py` homônimos.
Imports relativos além do package conhecido e múltiplos alvos locais JS/TS não são
adivinhados: `unresolved_imports` registra a localização e o motivo.
Não resolve imports dinâmicos, require, aliases tsconfig/bundler, pacotes externos
ou todas as raízes/layouts src de Python. JS lexical não é parser semântico completo;
Python 3.11 não aceita toda sintaxe de Python 3.12. Nenhuma inferência automática de
módulos de autenticação/persistência, papéis de frontend/backend ou testabilidade.
Componentes extensos mostram até vinte caminhos relacionados e a contagem total.

Assinatura de tipos gerados Supabase e comentários iniciais convencionais
`@generated` / `Code generated ... DO NOT EDIT` excluem somente heurísticas de
design, tamanho e duplicação. Não autenticam o gerador e não suprimem segurança.

## Package manager e workspaces

`packages` analisa até 100 package.json de 64 KiB, usando JSON estrito. Identifica
packageManager npm/pnpm/Yarn/Bun, lockfiles regulares presentes e workspace owner.
Workspaces package.json (lista ou objeto packages) e lista packages do
pnpm-workspace.yaml permitem herdar lockfile/manager do proprietário mais próximo.
Manifests fora de workspaces continuam independentes. Uma ausência de lockfile
compartilhado é reportada no proprietário, sem repetir em cada filho.

`MISSING_JS_LOCKFILE`, `CONFLICTING_JS_LOCKFILES` e
`PACKAGE_MANAGER_LOCK_MISMATCH` são suspeitas de revisão. Não lê conteúdo de
lockfiles para provar frescor/validade, nem executa installs. Nomes de diretórios e
symlinks não contam como lockfile. Yarn/pnpm YAML completo, anchors, listas inline,
exclusões e managers personalizados não são suportados: lacunas ficam explícitas,
com cobertura incompleta em vez de inferência silenciosa. Globs usam um subconjunto portátil por segmentos literais ASCII: `*` e `?` não atravessam `/`,
e `**` como segmento inteiro corresponde a zero ou mais níveis. Assim,
`packages/*` não inclui `packages/a/deep`, mas `packages/**` inclui. Prefixo `./`
e barra final são normalizados; vence o proprietário ancestral compatível mais
próximo. Braces, classes, extglobs, exclusões, segmentos vazios/intermediários,
`..` e `**` misturado a outros caracteres tornam a análise INCOMPLETE. Não é
compatibilidade integral com os dialetos npm/pnpm/Yarn/Bun, opções de dotfiles,
symlinks ou diferenças de versão. A semântica dos managers não foi validada por
instalações ou execução de seus scripts.

## Advisor determinístico

Valida assessment v1, classificações, IDs, caminhos e métricas estruturais; deduplica
achados idênticos e rejeita conflitos. Até 5000 achados; JSON até 8 MiB/profundidade 64,
sem chaves repetidas/constantes não finitas. Resolve o diretório pai confiável da entrada (incluindo `/tmp` → `/private/tmp` no
macOS), mas não aceita symlink/FIFO como arquivo final nem
sobrescreve o relatório de entrada. Textos arbitrários de mensagens e recomendações
não são encaminhados como instruções.

Ordens incluem problema/evidência, impacto potencial, confiança, prioridade de
revisão, arquivos prováveis, pré-requisitos, estratégia por regra, escopo mínimo,
aceite, testes, efeitos colaterais, rollback e bloqueios. Arquitetura reutiliza
`core.FLOWS['review']`; demais propostas usam o fluxo existente audit-fix.
Relatório incompleto, regra desconhecida ou evidência externa sem revisão bloqueiam
implementação. Nenhuma ordem é aplicada automaticamente.

`ready_for_proposal=false`: assessment não fornece snapshot autenticado. Obtenha
SHA base e blobs atuais pelo fluxo existente de escopo exato e revise um change-set
separadamente. JSON do Advisor não é um manifesto de gh-execute. Não há novo comando
HYBRID REFACTOR, segundo planejador ou aplicação de refatorações.

## Evidence Bridge — somente importação offline

~~~bash
python3 -m hybrid_engine evidence-import --report tests/fixtures/evidence/native-v1.json --report tests/fixtures/evidence/sarif-2.1.0.json --output /tmp/evidence.json
python3 -m hybrid_engine evidence-import --report /tmp/tool-report.json --format markdown
python3 -m hybrid_engine advise --report /tmp/evidence.json
~~~

Aceita um a oito relatórios JSON (até 8 MiB cada), 2000 resultados e 2000
caminhos de escopo globais, e
profundidade 64. A expansão de escopos repetidos por achado é limitada a 8 MiB,
e o JSON consolidado com indentação (incluindo newline) também deve caber em
8 MiB, para poder ser consumido pelo leitor do Advisor. Entradas pequenas não
podem expandir sem limite na saída. Os mesmos controles de leitura/parser do
Advisor são reutilizados.
Rejeita formatos malformados, caminhos externos e scope incompatível. Não baixa
artefatos, resolve referências externas, interpreta instruções ou executa comandos.
Fixtures são exclusivamente sintéticos e não exigem conta, scanner ou chave.

Contrato nativo `kind=external_evidence`, `schema_version=1`:

- tool: name/version identificadores limitados.
- target: code_sha opcional (40 hex minúsculos), repository opcional (`owner/repo`),
  environment (offline/fixture/staging/production/unknown), scope com arquivos relativos exatos.
- coverage.status: COMPLETE/INCOMPLETE/UNKNOWN, alegado pela ferramenta.
- findings: rule, path, line, severity (critical/high/medium/low), verification opcional
  e mapped_rule opcional para mapear uma regra Hybrid existente.

Estados declarados aceitos: SUSPECTED, NEEDS_VALIDATION, CONFIRMED_IN_ISOLATION,
CONFIRMED_IN_STAGING, FALSE_POSITIVE_REVIEWED e NOT_TESTED. Permanecem claims:
resultado normalizado é sempre suspected/NEEDS_VALIDATION. Um falso positivo
alegado não elimina o achado; uma confirmação alegada não confirma exploração.

A proveniência guarda ferramenta/versão, SHA256 do relatório, SHA e repositório declarados,
ambiente, severidade e verificação declaradas. `--expected-sha` compara somente a
alegação fornecida; não verifica bytes do código ou autoria. Divergência torna
cobertura incompleta. `source_sha_verification` continua NOT_VERIFIED mesmo quando
coincide. Dedup por regra mapeada/local/linha/SHA/ambiente/escopo preserva proveniências
e divergências; sem mapeamento explícito, regras de ferramentas distintas ficam
separadas. Repositórios declarados distintos ficam isolados. Sem SHA declarado,
cada arquivo/run é particionado pelo digest do relatório e índice do run: não se
presume um snapshot comum. Reimportar a mesma entrada ainda deduplica. Não tenta
adivinhar causa comum. Repositório e SHA são alegações não autenticadas.
O Advisor rejeita confiança promovida ou origem contraditória com proveniência
externa, exige um único vínculo de snapshot por finding e considera falhas da
enumeração mesmo se um resumo contraditório disser BOUNDED_COMPLETE.

Mensagens livres, snippets, comandos, anexos e URLs são OMITIDOS, em vez de tentar
redigir parcialmente um texto arbitrário. Identificadores/caminhos com padrões
reconhecíveis de credencial são rejeitados. Isso reduz vazamento, mas não detecta
todo segredo inventado em metadados: revise relatórios antes de compartilhá-los.

SARIF: somente 2.1.0, tool.driver.name/version, results com ruleId/level e uma
physicalLocation por resultado, URI relativa literal e startLine positivo.
Níveis error/warning/note/none mapeiam high/medium/low/low. Propriedades opcionais
run.properties.hybrid_scope/hybrid_code_sha/hybrid_environment/hybrid_repository e
result.properties.hybrid_rule têm o mesmo contrato nativo. Sem escopo exato ou
invocations.executionSuccessful=true declarados, cobertura fica INCOMPLETE.
URIs absolutas/remotas, uriBaseId, artifact index, múltiplas locations e suppressions
não são suportados; use o contrato nativo para preservar claims de falso positivo.

Saída consolidada reutiliza assessment v1; Advisor aceita proveniência estruturada
e bloqueia a execução até revisão independente. Não implementa adaptadores de
Cloudflare/Codex Security/Strix/Supabase, scanners, validação dinâmica ou pentest.
Nenhuma dependência, serviço pago, Docker ou modelo é obrigatório.

## Evidência e continuidade

Consulte [EXECUTION_PLAN.md](EXECUTION_PLAN.md) para testes realmente executados,
comparações dos pilotos, medições, commits e limitações remanescentes.
CI hospedado continua CI_NOT_VERIFIED, separado dos testes locais.
