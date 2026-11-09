# Como contribuir com o Hybrid Engine

Obrigado por ajudar a testar o framework! O objetivo é receber **evidências de uso real**, não apenas avaliações genéricas.

[Início rápido](docs/COMECE_AQUI.md) · [Exemplos de comando](docs/EXEMPLOS_DE_COMANDOS.md) · [Segurança](docs/SECURITY.md)

## Beta fechado

O repositório permanece **privado** enquanto os testes iniciais são realizados. Pessoas interessadas precisam receber acesso do responsável; não é necessário (e não é recomendado) compartilhar repositórios privados pessoais com outros testadores.

Se tiver permissão para criar uma Issue, utilize um título claro, por exemplo:
`[Beta] HYBRID DEBUG — falhou ao produzir PR Draft`.

Descreva:

- **Ambiente:** ChatGPT com conexão GitHub / outro agente / CLI Python, com versões relevantes se disponíveis;
- **Objetivo e comando enviado:** substitua dados sigilosos por placeholders;
- **Resultado esperado vs. observado;**
- **Evidências reais:** branch/PR/commit, mensagens de erro, nome dos testes executados e respectivos status;
- **Reprodução:** passos mínimos, em repositório de teste autorizado e sem credenciais;
- **Impacto:** baixo / médio / alto, e limitações de acesso.

Use `PASSED`, `FAILED` e `NOT_RUN` separadamente. Um check bloqueado por cota ou um teste sem executor é `NOT_RUN`, não um bug automaticamente corrigido.

## Como enviar mudanças

1. Consulte `AGENTS.md` e o guia específico do recurso.
2. Escolha um problema pequeno e investigue a causa.
3. Trabalhe numa branch separada; **não edite `main` diretamente**.
4. Adicione testes offline quando possível e registre comandos/resultado.
5. Abra uma **PR Draft**, com motivação, arquivos afetados, evidências, impacto, riscos e rollback.
6. Aguarde revisão antes de qualquer merge; deploy e alterações de produção não fazem parte do processo genérico.

Teste local do framework:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q hybrid_engine tests
python3 -m hybrid_engine --help
```

O CI hospedado é evidência adicional, não substituto para testes que não rodaram. Evite loops de commits/workflows apenas para obter um check verde.

## Segurança e confidencialidade

**Nunca publique** valores de chaves, tokens, arquivos `.env`, dados pessoais, bases privadas, partes sensíveis de código de terceiros ou detalhes reproduzíveis de exploração em Issues públicas. Vulnerabilidades devem ser reportadas de forma privada ao responsável pelo repositório, pelo canal que ele disponibilizar.

A execução de scripts de repositórios desconhecidos pode produzir efeitos colaterais. Prefira um ambiente isolado, limite a rede, reveja comandos e preserve logs sem segredos.

## Ideias de feedback útil

- O agente conseguiu abrir a documentação sem depender do contexto anterior?
- O comando estava claro para alguém que nunca usou o framework?
- A análise encontrou um problema real ou apenas suspeitas?
- As alterações respeitaram a branch e as permissões?
- Os testes executados foram claramente diferenciados dos não executados?
- Algum passo consumiu CI ou recursos externos desnecessariamente?

O foco da v0.8 é **confiabilidade e simplicidade**. Sugestões que adicionem complexidade devem demonstrar um problema real que resolvem.

[Voltar ao README](README.md) · [Licença MIT](LICENSE)
