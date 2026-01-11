# Chat Components

Este módulo implementa os componentes de chat do Friday TUI seguindo as melhores práticas do [Textual](https://textual.textualize.io/).

## Arquitetura

Baseado no artigo [Anatomy of a Textual User Interface](https://textual.textualize.io/blog/2024/09/15/anatomy-of-a-textual-user-interface/), os componentes de chat usam:

- **Widgets Markdown** para renderização de mensagens com suporte a formatação
- **VerticalScroll** como container para auto-scroll e rolagem
- **CSS dedicado** para estilização de cada tipo de mensagem

## Componentes

### UserPrompt
Widget para mensagens do usuário. Exibe texto alinhado à direita com cor primária.

```python
from friday.app.tui import UserPrompt

prompt = UserPrompt("Hello, how are you?")
```

### AssistantResponse
Widget para respostas do assistente. Exibe texto alinhado à esquerda com cor de sucesso.

```python
from friday.app.tui import AssistantResponse

response = AssistantResponse("I'm doing great, thanks!")
```

### ToolResponse
Widget para saídas de ferramentas. Exibe texto com cor de aviso (warning).

```python
from friday.app.tui import ToolResponse

tool_result = ToolResponse("Screenshot saved: /tmp/screenshot.png")
```

## Layout

O chat usa um `VerticalScroll` container que:
- Auto-scroll automático quando novas mensagens são adicionadas
- Suporte a rolagem com mouse/teclado
- Ajuste automático de tamanho

## Estilização (TCSS)

```css
UserPrompt {
    background: $primary 10%;
    margin: 1;
    margin-right: 8;
    padding: 1 2 0 2;
    border: round $primary;
}

AssistantResponse {
    background: $success 10%;
    margin: 1;
    margin-left: 8;
    padding: 1 2 0 2;
    border: round $success;
}

ToolResponse {
    background: $warning 10%;
    margin: 1;
    padding: 1 2 0 2;
    border: round $warning;
}
```

## Testes

### Testes Unitários
```bash
uv run pytest tests/test_chat_widgets.py -v
```

Testa:
- Widgets são instâncias de Markdown
- Aceitam conteúdo formatado em Markdown

### Testes de Integração
```bash
uv run pytest tests/test_chat_integration.py -v
```

Testa:
- Chat view existe após mount
- Mensagens de usuário/assistente/tool são adicionadas corretamente
- Múltiplas mensagens funcionam em sequência
- Input submit cria mensagem de usuário
- Formatação Markdown é preservada

## Uso

### Adicionar mensagem ao chat

```python
async with app.run_test() as pilot:
    await app._write_chat("user", "Hello")
    await app._write_chat("assistant", "Hi there!")
    await app._write_chat("tool", "Task completed")
```

### Com suporte a Markdown

```python
markdown_text = """
# Heading

**Bold** and *italic* text

```python
print("code block")
```
"""

await app._write_chat("assistant", markdown_text)
```

## Melhorias Futuras

- [ ] Suporte a streaming de respostas (chunks)
- [ ] Timestamps nas mensagens
- [ ] Avatar/ícone por tipo de mensagem
- [ ] Exportar conversa como Markdown
- [ ] Busca/filtro de mensagens
- [ ] Temas customizáveis por tipo de mensagem
