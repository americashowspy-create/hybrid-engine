# HYBRID AUTO — protocolo universal para agentes de IA (v0.8)

[README](../README.md) · [Comece aqui](COMECE_AQUI.md) · [Comandos prontos](EXEMPLOS_DE_COMANDOS.md) · [Instruções do agente](../AGENTS.md)

## O que é

O Hybrid Engine é um **protocolo de orquestração agnóstico ao agente**. Ele reúne, em implementação própria, planejamento de tarefas, investigação de falhas, revisão de alterações, verificações de segurança, gestão de escopo, handoff de código e relatórios rastreáveis.

Não é um modelo de IA, plugin embutido nem coleção completa de ferramentas externas. Pode ser seguido em um chat com conectores, em um agente de código, numa IDE ou via CLI, **desde que o ambiente disponha das ferramentas e permissões necessárias**.

## Comando padrão

```text
HYBRID AUTO — v0.8

Framework: https://github.com/americashowspy-create/hybrid-engine
Projeto: https://github.com/OWNER/REPOSITORY

Leia AGENTS.md e docs/AGENT_AUTO.md na main do framework.
Leia também as instruções do repositório alvo, quando existirem.

Inspecione a branch padrão, o HEAD SHA, as PRs existentes e o acesso real.
Identifique um problema comprovado e de baixo risco.
Defina escopo, critérios de aceite e rollback.
Quando autorizado e tecnicamente possível, corrija em branch isolada,
execute testes seguros e abra uma PR Draft com evidências e links reais.

Não faça merge, deploy, migrações, mudanças de credenciais ou produção.
Não declare testes não executados como aprovados.
Não crie execuções de CI desnecessárias.
Se houver bloqueio, informe a limitação e entregue diagnóstico/patch.
```

## Ambientes compatíveis com o protocolo

| Modalidade | O que pode fazer | Condição necessária |
| --- | --- | --- |
| Chat com ferramentas | Ler documentação, investigar e eventualmente escrever no GitHub. | Conexão efetiva com permissões de leitura/escrita; muitas são somente leitura. |
| Agente de programação / IDE | Inspecionar um checkout, editar arquivos e executar testes. | Sistema de arquivos, terminal e GitHub acessíveis e autorizados. |
| CLI Python opcional | Gerar planos, auditorias, pacotes de fontes e validar propostas. | Python 3.11+, credenciais de escopo mínimo para operações remotas; **não gera patches de IA sozinha**. |
| Adaptador local | Receber JSON/stdio e devolver manifesto de patch. | Executável confiável, configuração própria e isolamento quando apropriado. |

**Protocolo compatível não significa integração oficialmente testada em todas as plataformas.** Uma URL não fornece acesso, um chat só de leitura não abre PR e um executor externo não é automaticamente sandboxed.

## Processo e critérios de qualidade

1. **Descoberta:** identificar branch, commit, arquitetura, convenções, permissões e correções já iniciadas.
2. **Diagnóstico:** reproduzir/caracterizar a causa de um problema. Separar `CONFIRMED` de `SUSPECTED`.
3. **Escopo e plano:** delimitar arquivos auditados, registrar hashes Git, critérios de aceite e plano mínimo. Evitar mudanças não relacionadas.
4. **Implementação controlada:** usar branch isolada e validar commit/base/arquivo antes de cada proposta. Não editar diretamente a branch principal.
5. **Verificação:** executar testes seguros possíveis e registrar comando, ambiente, saída e status. `NOT_RUN` não equivale a `PASSED`. O CI hospedado é uma evidência separada.
6. **Entrega:** incluir PR Draft se autorizada e viável, relatório, alterações, evidências, riscos e procedimento de rollback.
7. **Continuidade:** registrar estado/decisões no projeto quando necessário, sem criar rastreadores concorrentes.

## Proteções e limitações

- Projetos de finanças, credenciais, autenticação, autorização, migrações, controles físicos ou infraestrutura crítica exigem investigação somente leitura por padrão e aprovação específica para ações de risco.
- Não executar código de origem desconhecida cegamente. Scripts de testes podem ter efeitos colaterais. Prefira ambientes isolados e revisão prévia.
- Uma auditoria estática é heurística, **não um pentest**. A CLI limita auditorias amplas a 250 arquivos; pacotes usam até 20 arquivos exatos, com até 64 KiB por fonte.
- Bundle privado não deve ser publicado em logs ou issues; SHA verifica integridade do conteúdo, não autentica a identidade de quem produziu o pacote.
- Evite consumo de GitHub Actions desnecessário. Testes locais não usam minutos de Actions, mas sandboxes/servidores podem ter custos próprios.
- **Nenhum merge, deploy, mudança de produção ou autorização implícita** é concedido por `HYBRID AUTO`.

## Execução opcional pela CLI

```bash
hybrid gh-audit --repo OWNER/REPO --ref main
hybrid gh-chat-package --repo OWNER/REPO \
  --goal "HYBRID DEBUG: corrigir problema" \
  --path src/app.py --output /tmp/hybrid-chat.json
hybrid gh-execute --bundle /tmp/hybrid-chat.json \
  --manifest /tmp/reviewed-change.json
# Apenas com autorização explícita: --apply abre uma PR Draft.
```

O manifesto é preparado e revisado por agente/desenvolvedor; a CLI não o inventa. Consulte [documentação técnica GitHub](GITHUB_ADAPTER.md) e [adaptador de agente](UNIVERSAL_EXECUTOR.md).

## Resultado esperado

```text
STATUS: PR_DRAFT_OPEN / BLOCKED / READ_ONLY_REPORT
BASE: [commit SHA verificado]
ARQUIVOS: [caminhos e hashes verificados]
MUDANÇAS: [o que foi aplicado ou proposto]
TESTES LOCAIS: PASSED / FAILED / NOT_RUN (com evidências)
CI GITHUB: PASSED / FAILED / NOT_RUN (verificado no HEAD)
RISCOS: [limites]
ROLLBACK: [procedimento]
PRODUÇÃO: UNCHANGED
```

É um **formato de relatório**, não garantia de sucesso. Nunca fabrique SHAs, testes ou links.

[Guia para iniciantes](COMECE_AQUI.md) · [Protocolos detalhados de segurança](SECURITY.md)
