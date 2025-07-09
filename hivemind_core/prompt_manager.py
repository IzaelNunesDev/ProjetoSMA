import json
from pathlib import Path

class PromptManager:
    def __init__(self, prompts_directory: str = "prompts"):
        self.base_path = Path(__file__).parent / prompts_directory
        self.prompts = self._load_prompts()

    def _load_prompts(self):
        loaded_prompts = {}
        for prompt_dir in self.base_path.iterdir():
            if prompt_dir.is_dir():
                metadata_path = prompt_dir / "prompt.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        task_name = prompt_dir.name
                        
                        template_path = prompt_dir / metadata["template_file"]
                        if template_path.exists():
                            metadata["template"] = template_path.read_text(encoding="utf-8")
                            loaded_prompts[task_name] = metadata
                        else:
                            print(f"Aviso: Arquivo de template {template_path} não encontrado para a tarefa {task_name}.")
                else:
                    print(f"Aviso: prompt.json não encontrado em {prompt_dir}")
        return loaded_prompts

    def get_prompt_template(self, task_name: str) -> str | None:
        """Retorna o template de prompt para uma tarefa específica."""
        if task_name in self.prompts:
            return self.prompts[task_name].get("template")
        return None

    def format_prompt(self, task_name: str, **kwargs) -> str | None:
        """Formata um prompt com os argumentos fornecidos."""
        template = self.get_prompt_template(task_name)
        if template:
            return template.format(**kwargs)
        return None

# Singleton para ser usado em toda a aplicação
prompt_manager = PromptManager() 