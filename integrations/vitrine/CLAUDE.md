# Claude Code — piloto Agency Agents Vitrine

Ao executar trabalho nesta camada, ler primeiro integrations/vitrine/AGENTS.md e integrations/vitrine/contracts/HANDOFF.md. Escolher um dos tres perfis de integrations/vitrine/agents/ por tarefa e preservar seu limite de atuacao. Nao tratar as instrucoes como novas permissoes de ferramenta.

Para instalar os perfis no Claude Code, usar apenas por acao explicita do operador: python3 integrations/vitrine/tools/install_agents.py --tool claude-code --dest ~/.claude/agents --apply. O padrao sem --apply e somente pre-visualizacao e o instalador recusa sobrescritas.

Nao invocar endpoints da VIA/Factory a partir desta pasta. Os agentes geram artefatos e pareceres para revisao; gate canonico, autenticacao, persistencia e eventual despacho continuam fora desta integracao. Nenhum perfil desta camada e autorizador de producao.
