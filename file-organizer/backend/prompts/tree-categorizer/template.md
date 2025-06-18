Esta é a estrutura de diretórios de uma pasta que será organizada:

{tree}

Seu objetivo é:
- Sugerir pastas que podem ser reorganizadas ou movidas, mas nunca quebrar a lógica de projetos/jogos/programas.
- Nunca reorganize subpastas internas de uma estrutura lógica.
- Nunca reorganize nada dentro de pastas como "Assets", "cfg", "shaders", "venv", "node_modules", "src", "bin", "logs".

Analise a árvore e retorne APENAS um objeto JSON com duas chaves:
1. "analysis": Uma breve análise em texto sobre a estrutura geral (ex: "A pasta parece conter um projeto de jogo, um projeto web e alguns documentos soltos.").
2. "suggestions": Uma lista de ações sugeridas. Cada ação é um dicionário com "action": "MOVE_FOLDER", "from": "caminho/relativo/pasta", "to_category": "Nova Categoria Sugerida". Se nenhuma ação for necessária, retorne uma lista vazia.

Exemplo de Saída:
```json
{
  "analysis": "A estrutura contém o jogo 'AssettoCorsa' e uma pasta solta de documentos 'Meus Textos'.",
  "suggestions": [
    {
      "action": "MOVE_FOLDER",
      "from": "Meus Textos",
      "to_category": "Documentos Pessoais"
    }
  ]
}
