# DB Guard — v0.9 experimental (primeira fase)

O DB Guard é uma **auditoria estática e offline** integrada ao Hybrid Engine. Funciona sem senha de banco, sem conexão de rede e sem executar SQL ou scripts do projeto. É agnóstico ao agente e ao fornecedor de banco de dados.

## Executar

~~~bash
hybrid db-audit --target /caminho/do/projeto
hybrid db-audit --target /caminho/do/projeto --output /tmp/db-guard.json
hybrid run --target /caminho/do/projeto --intent "HYBRID AUTO"
hybrid run --target /caminho/do/projeto --intent "HYBRID DB-AUDIT"
~~~

O fluxo AUTO inclui o relatório DB Guard nos relatórios locais quando identificar sinais de banco de dados. A execução explícita do db-audit **não cria nem modifica** arquivos por padrão; --output solicita gravação de um relatório. O fluxo run continua a criar os relatórios habituais em .hybrid/. Nenhum teste é executado sem --tests.

## As sete áreas e o que realmente é verificado

| Área | Nesta fase | O que NÃO é verificado |
| --- | --- | --- |
| Segurança | Nomes de variáveis privilegiadas com prefixo público; indícios de RLS desligada, policies SQL amplas e regras abertas de Firestore | Acesso real, GRANT, RLS efetivo, permissões ou rede |
| Backup | Checklist explícito de evidências necessárias | Existência, retenção, sucesso de restauração e RPO/RTO |
| Custos | Checklist explícito | Consumo real, faturamento, quantidade de leituras ou limites |
| Transações | Checklist explícito | Atomicidade de operações de negócio |
| Modelagem | Valores monetários em Float/REAL/DOUBLE; timestamps de eventos sem timezone | Constraints reais, dados existentes e integridade |
| Migrations | SQL destrutivo em arquivos de migrations | Schema drift ou rollback executável |
| Performance | OFFSET constante elevado em SQL | Índices reais, EXPLAIN ou planos de produção |

Os achados são **suspeitas** para triagem humana, não falhas confirmadas. A seção verification marca todas as sete áreas como NOT_VERIFIED em relação à segurança e ao comportamento reais do banco. Nenhuma recomendação cria migrations automaticamente.

## Segurança operacional

- Ignora diretórios de dependências/artefatos, links simbólicos, binários, arquivos grandes e arquivos .env reais; examina apenas nomes de variáveis em templates de ambiente.
- Até 250 arquivos candidatos, 256 KiB por arquivo e 500 achados. Limites ou arquivos ignorados resultam em INCOMPLETE, não em aprovação.
- Relatórios incluem caminho, linha, regra e mensagem, **nunca o valor correspondente** nem trecho do código.
- NÃO acessa banco em produção, NÃO executa EXPLAIN ANALYZE, NÃO testa restaurar backup, NÃO roda migrations.
- Por design, o módulo não determina política RLS efetiva, se existe backup ou quanto o projeto custa.

## Próximos passos, separados e autorizados

1. Permitir regras por tecnologia e supressões justificadas para achados falsos positivos.
2. Conector de metadados **somente leitura** com autorização explícita e credenciais de escopo mínimo, para comparar schema, permissões, estatísticas e estratégias de backup.
3. Testes de rollback e restauração em banco descartável; propostas de migrations/índices em PR Draft, sem aplicar em produção.

**Referência conceitual:** artigo Banco de Dados — Fundamentos para Vibe Coders EP2 (12/11/2026), https://manodeyvin.com.br/p/banco-de-dados-fundamentos-para-vibe. Esta implementação contém apenas heurísticas próprias e não copia os prompts nem afirma executar as auditorias completas descritas no artigo.
