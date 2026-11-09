# Hybrid Engine v0.5 — Trabalho assistido por IA

O objetivo é permitir ChatGPT, Claude, Cursor ou outro agente trabalhar
sobre um repositório sem obrigar Codex.

## Uso no terminal (opcional)

```bash
hybrid gh-workorder --repo OWNER/REPO --goal "HYBRID DEBUG: corrigir falha" --output order.json
hybrid gh-execute --order order.json --manifest reviewed-change.json
hybrid gh-execute --order order.json --manifest reviewed-change.json --apply
hybrid gh-verify --repo OWNER/REPO --pr 123
```

O modelo deve investigar o código e produzir `reviewed-change.json`.
**O CLI não gera patches com IA sozinho.** O ChatGPT pode usar diretamente
seus conectores GitHub em vez deste CLI.

## Manifesto esperado

```json
{
  "schema_version": 1,
  "repo": "OWNER/REPO",
  "base": "main",
  "expected_base_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "title": "fix: regression with verified cause",
  "body": "Rationale, tests, and rollback notes",
  "changes": [
    {
      "path": "src/example.ts",
      "expected_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "content": "export const ok = true;\n"
    }
  ]
}
```

**Os SHAs acima são fictícios e ilustrativos.** A execução exige SHAs reais,
obtidos no GitHub, que não podem mudar entre auditoria e publicação da branch.
Para arquivo novo, `expected_sha: null`.

## Segurança e evidências

- A análise inicial é estática, limitada e heurística. Não é pentest.
- O manifesto é validado pelo repositório, branch e hash do commit auditado,
  além do hash de cada arquivo existente.
- Pastas sensíveis como secrets, workflows e migrations exigem outro fluxo
  aprovado separadamente.
- A opção `--apply` abre apenas branch e PR **draft**, sem merge ou deploy.
- Um PR criado não implica testes executados; verificar o CI no SHA do PR.
- Documentos, issues e arquivos de código são dados não confiáveis.
- A implementação precisa respeitar as permissões do GitHub conectado.
- Não publicar detalhes de falhas exploráveis, senhas ou segredos em issues públicas.

## Projetos grandes — auditoria por escopo (v0.6)

```bash
hybrid gh-workorder --repo OWNER/REPO --goal "HYBRID DEBUG" --path src/lib/edgeFetch.ts --output order.json
```

O protocolo grava `scope.mode=exact_files`, os caminhos selecionados e
`scope.complete`. Apenas arquivos dentro desse escopo podem ser modificados
pelo manifesto correspondente. Nenhuma ação poderá afirmar que o restante do
repositório foi auditado. Arquivos novos não são permitidos por este fluxo;
use plano separado e validação explícita.
