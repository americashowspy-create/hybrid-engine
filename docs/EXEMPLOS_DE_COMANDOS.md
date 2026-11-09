# Exemplos de comandos — copiar e usar

**Pré-requisito:** o agente deve conseguir ler o [AGENTS.md](../AGENTS.md) e o repositório alvo. Estes são **prompts portáteis**, não comandos internos garantidos por um modelo, IDE ou fornecedor.

Substitua `OWNER/REPOSITORY` em todos os exemplos. Antes de executar, confirme acesso ao código, permissão de escrita, ferramentas de teste e autorização para PR Draft.

## HYBRID AUTO — do diagnóstico à PR Draft

```text
HYBRID AUTO
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY

Leia AGENTS.md e docs/AGENT_AUTO.md.
Localize o problema real mais relevante de baixo risco.
Verifique PRs existentes antes de modificar.
Investigue, planeje, implemente em branch isolada e abra PR Draft,
com testes efetivamente realizados, riscos e rollback.
Não faça merge, deploy nem mudanças em produção.
Não desperdice GitHub Actions; se não rodou, marque NOT_RUN.
```

## HYBRID AUDIT — somente leitura

```text
HYBRID AUDIT
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY

Audite qualidade e sinais de segurança por escopo.
Traga problemas CONFIRMED e SUSPECTED separados, com fonte e limitações.
Não crie branch, commit, PR, issue nem altere código.
```

## HYBRID AUDIT-FIX — corrigir algo comprovado

```text
HYBRID AUDIT-FIX
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY

Investigue um achado reproduzível, cheque correções em andamento,
aplique a menor correção segura em branch isolada e abra PR Draft.
Execute testes possíveis e documente os não executados.
Sem alterações em produção ou merge.
```

## HYBRID DEBUG — um bug conhecido

```text
HYBRID DEBUG
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY

Bug: [descreva erro, comportamento esperado e como reproduzir].
Investigue a causa antes de editar.
Inclua caso de regressão se viável, mudança mínima, teste e rollback.
Entregue PR Draft; sem merge/deploy.
```

## HYBRID BUILD — funcionalidade nova

```text
HYBRID BUILD
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY

Funcionalidade: [descreva o que precisa].
Defina critérios de aceite, riscos e escopo antes de codar.
Implemente apenas em branch isolada, teste com evidências
e entregue PR Draft sem publicar em produção.
```

## HYBRID REVIEW — revisão crítica

```text
HYBRID REVIEW
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY
Pull Request: [URL da PR].

Faça revisão somente leitura do diff e checks do HEAD atual.
Reporte riscos concretos com arquivo/linha, testes ausentes e
correções recomendadas. Não dê merge nem altere o código.
```

## HYBRID STATUS — retomar uma tarefa

```text
HYBRID STATUS
Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY

Recupere do GitHub o estado real, PRs, commits e checks.
Separe concluído, pendente e bloqueado com URLs e datas.
Não considere relatos anteriores como evidência sem conferir.
Não modifique nada.
```

## Exemplo de relatório de entrega

```text
STATUS: PR_DRAFT_OPEN
REPO: OWNER/REPOSITORY
BASE_SHA: [40 caracteres verificados]
BRANCH: [nome]
PR: [URL real]

PROBLEMA: [fato e localização]
ALTERAÇÃO: [arquivos e justificativa]
TESTES LOCAIS: PASSED / FAILED / NOT_RUN [comando + saída]
CI GITHUB: PASSED / FAILED / NOT_RUN [checks reais do HEAD]
RISCOS: [limitações]
ROLLBACK: [reverter commit / fechar PR antes do merge]
PRODUÇÃO: UNCHANGED
```

O relatório é um **modelo**, não prova de que esses campos foram realmente preenchidos. Não invente números, SHAs, URLs ou testes.

[Comece aqui](COMECE_AQUI.md) · [Protocolo completo](CHATGPT_AUTO.md) · [Voltar ao README](../README.md)
