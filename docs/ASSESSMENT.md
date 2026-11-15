# Audit Intelligence — v0.10 em desenvolvimento

A primeira entrega do Audit Intelligence é uma **avaliação estática e offline** de um projeto, com achados normalizados e recomendações revisáveis. Ela não altera código, não executa scripts, não acessa a internet nem consulta bancos de dados.

> **Estado:** implementação experimental na branch feat/audit-intelligence-v010. A versão oficial da main ainda é v0.9.0. Nenhuma publicação v0.10 está homologada.

## Como experimentar em um checkout da branch

Python 3.11+ na raiz do repositório:

~~~bash
python3.11 -m hybrid_engine assess --target /caminho/do/projeto
python3.11 -m hybrid_engine assess --target /caminho/do/projeto --format markdown
python3.11 -m hybrid_engine assess --target /caminho/do/projeto --format json --output /tmp/assessment.json
python3.11 -m unittest discover -s tests -q
~~~

O programa imprime o relatório por padrão. Somente escreve um arquivo de relatório quando o usuário informa explicitamente a opção `--output`. Nenhum arquivo `.hybrid/` é criado pelo comando assess.

## Cobertura implementada na fase 1

O relatório combina três fontes:

1. **Scanner geral existente:** sinais de stack e padrões estáticos de segurança.
2. **DB Guard v0.9:** riscos heurísticos em SQL, Firebase, Prisma e configuração; mantém as sete áreas de verificação real como `NOT_VERIFIED`.
3. **Arquitetura/qualidade de código:** arquivos-fonte acima de 500 linhas (exceto tipos Supabase reconhecidos por assinatura de conteúdo como gerados), duplicações byte a byte de arquivos-fonte de pelo menos 1024 bytes, ausência de testes com nomes convencionais nos arquivos elegíveis, e ausência de lockfile reconhecido quando existe `package.json` na raiz.

Essas regras são **indicadores limitados**, não conclusões sobre boa ou má arquitetura. Por exemplo, dois arquivos iguais podem ser intencionais, um arquivo longo pode ser bem organizado, testes podem usar nomes diferentes e um projeto pode não adotar lockfile por decisão explícita.

## Contrato da avaliação

- `schema_version`, `mode=static_read_only`, `status`, `target`, `stack`.
- `coverage`: contagem de arquivos, leitura incompleta, arquivos ignorados e truncamentos, incluindo a cobertura independente do DB Guard.
- `findings`: IDs estáveis, origem, categoria, severidade, localização, confiança `suspected`, contexto `test_source` ou `application_source` e mensagem sem snippets. Uma correspondência em arquivos de testes **permanece visível e com sua severidade original**, pois credenciais verdadeiras também podem acabar em testes.
- `summary`: contagens separadas de achados em código de aplicação e código de teste; nenhuma contagem implica que achados de testes são falsos.
- `coverage.generated_types_excluded_from_size_rule`: número de tipos Supabase com assinatura reconhecida dispensados **apenas** da heurística de arquivo longo; demais regras continuam ativas.
- `recommendations`: prioridade **de revisão**, justificativa, ação sugerida, aceite, validação e rollback. O status é sempre `PROPOSED_NOT_APPLIED`; nenhuma recomendação é executada.
- `verification`: testes do alvo `NOT_RUN`, verificações de banco real `NOT_VERIFIED` e análise de runtime `NOT_VERIFIED`.
- `limitations`: explica lacunas e impedimentos.

Os achados observados no primeiro piloto do próprio Hybrid Engine estão em testes com tokens deliberadamente sintéticos. A classificação contextual ajuda na triagem, **sem suprimir automaticamente achados de credenciais em testes**.

O relatório marca `INCOMPLETE` quando a cobertura é truncada ou algum arquivo relevante não pôde ser lido. `NO_FINDINGS` **não** significa que o projeto está seguro ou sem problemas.

## Regras operacionais

- Sem execução de código ou testes do projeto avaliado, rede, SQL, migrações ou conexão de banco.
- Arquivos `.env` reais não são abertos pelo novo scanner geral; o DB Guard só examina variáveis em modelos de ambiente, nunca valores nos relatórios.
- Ignora symlinks, diretórios típicos de dependências/artefatos e binários; analisa até 250 arquivos elegíveis, no máximo 256 KiB cada, respeitando também os limites independentes do DB Guard.
- Não inclui valores de credenciais nem trechos de código nos relatórios. Pacotes de fontes para agentes externos continuam sujeitos às regras de privacidade próprias.
- Não cria branches, commits, pull requests, deploys nem modifica produção.

## Critérios de homologação antes do lançamento

- Regressão completa dos 135 testes da v0.9 e aprovação dos testes novos na versão Python 3.11. A primeira implementação registrou **147/147 PASS** no Mac em 15/11/2026; as regressões adicionais de classificação contextual **ainda exigem reexecução** antes da PR.
- Inspeção de arquivos alterados, compilação e testes de CLI.
- Piloto no Radar Artístico em checkout isolado, sem mudanças no projeto.
- Verificar que não houve vazamento de valores de ambiente e que resultados incompletos são identificados corretamente.
- Registrar `CI_NOT_VERIFIED` enquanto o GitHub Actions permanecer bloqueado por faturamento.

## Fora desta fase

Análise semântica profunda de AST e arquitetura, verificação efetiva de RLS/GRANT, custos reais, performance em runtime, integração com modelo de IA, geração automática de patches, aplicação de refatorações e auditoria contínua.

A **fase 2** usará o relatório estável para o AI Implementation Advisor; System Design / HYBRID REFACTOR e monitoramento ficarão em fases posteriores.

Escopo e critérios detalhados: [Issue #13](https://github.com/americashowspy-create/hybrid-engine/issues/13).

## Incremento de robustez e Advisor (branch de desenvolvimento)

A leitura agora é limitada também no momento de abrir o arquivo e usa descritores
relativos ao diretório, sem seguir symlinks em componentes intermediários.
Arquivos especiais (incluindo FIFOs) não são lidos; erros ao percorrer diretórios
contam como cobertura incompleta. A implementação exige suporte POSIX a `dir_fd`
e `O_NOFOLLOW`; em plataformas sem esses recursos os arquivos ficam ignorados e a
cobertura é `INCOMPLETE`, em vez de enfraquecer silenciosamente a leitura.
A raiz informada é resolvida explicitamente; o scanner não é uma sandbox contra
um adversário com controle do processo/sistema de arquivos inteiro.

`REACT_HTML_INJECTION` identifica um ponto de renderização de HTML. HTML estático
confiável e HTML sanitizado continuam como pistas de revisão; o scanner não faz
análise de fluxo, não valida sanitizadores e não declara exploração comprovada.
A recomendação pede rastrear origem, interpolação e fronteira de confiança.

A classificação de testes inclui `.test.jsx`, `.spec.jsx` e `_test.go`.
Um arquivo JSON de configuração chamado `test_*` não comprova existência de testes.
Diretórios e symlinks com nome de lockfile não contam como lockfile regular.
Nomes de arquivo são escapados no Markdown; continuam sendo metadados potencialmente
sensíveis. Não compartilhe relatórios sem revisar caminhos e escopo.

### AI Implementation Advisor

~~~bash
python3 -m hybrid_engine assess --target /projeto --output /tmp/assessment.json
python3 -m hybrid_engine advise --report /tmp/assessment.json
python3 -m hybrid_engine advise --report /tmp/assessment.json --format markdown --output /tmp/advice.md
~~~

O Advisor é determinístico, offline e não usa LLM nem dependências novas. Consome
assessment `schema_version=1`, verifica classificações, IDs e caminhos relativos,
deduplica achados idênticos e rejeita duplicatas conflitantes. Rejeita JSON com
chaves repetidas, constantes não finitas, mais de 64 níveis, mais de 8 MiB ou mais
de 5000 achados. Não aceita symlink/FIFO como entrada. Não sobrescreve o próprio
relatório de entrada. Saída só é gravada mediante `--output`.

Cada ordem inclui evidência estrutural, confiança, prioridade de revisão, impacto
potencial, estratégia por regra, escopo mínimo, pré-requisitos, aceite, testes,
efeitos colaterais, rollback, bloqueios e fluxo existente. Textos arbitrários do
relatório (mensagens, recomendações e instruções embutidas) não são encaminhados.
Regras desconhecidas exigem diagnóstico manual (`BLOCKED`). Cobertura incompleta
bloqueia a passagem para implementação, mesmo quando não existem achados.

As ordens são propostas de investigação/implementação (`PROPOSED_NOT_APPLIED`),
não patches. `ready_for_proposal=false` é intencional: o relatório não garante
snapshot ou autenticidade. Antes de uma implementação, reutilize o fluxo de
escopo exato existente e obtenha SHA base e blob SHA atuais. Não passe o JSON do
Advisor diretamente para `gh-execute`: ele não é um manifesto desse executor.

### System Design / proposta de refatoração

A primeira entrega reaproveita os achados `LARGE_SOURCE_FILE` e
`EXACT_DUPLICATE_SOURCE` e o fluxo `review`, com avaliação de custo-benefício,
interfaces/imports, aceite e rollback. Não cria outro planejador e não adiciona
um comando HYBRID REFACTOR. Não há AST, grafo de dependências, análise de acoplamento
ou detecção semântica de duplicação. Tamanho e igualdade de bytes são apenas
indicadores; nenhuma refatoração é aplicada ao projeto avaliado.

O Evidence Bridge permanece pendente: o contrato interno foi reforçado primeiro.
Não há importador SARIF, adaptador externo, validação dinâmica nem pentest.

O scanner geral também limita sua saída a 2000 achados; um excedente produz
`coverage.truncated=true` e `INCOMPLETE`. O DB Guard conserva seu limite independente
de 500 achados. `vendor/`, `target/` e `.cache/` ficam excluídos consistentemente dos
scanners. A enumeração do filesystem ainda depende de `os.walk` e não possui timeout
ou orçamento global de entradas: projetos com milhões de arquivos ignorados podem
ser lentos. Não há promessa de imunidade a exaustão de recursos nesse cenário.

Duplicações exatas preservam `related_paths` como evidência estrutural, para que o
Advisor inclua ambos os arquivos prováveis sem incorporar seus nomes em mensagens.
IDs permanecem baseados em origem/regra/caminho/linha: são determinísticos no mesmo
snapshot, mas uma inserção de linhas pode mudá-los. Não são identidade semântica.
