import yaml
from ai_server.decorators.singleton import singleton
from ai_server.log.bot_factory_logger import BotFactoryLogger


YAML_DIRECTORY = "config"

ANSWER_YAML = f"{YAML_DIRECTORY}/answer.yaml"
BEHAVIOUR_YAML = f"{YAML_DIRECTORY}/behaviour.yaml"
QUALITIES_FLAWS = f"{YAML_DIRECTORY}/qualities_flaws.yaml"
PROMPTS = f"{YAML_DIRECTORY}/prompts.yaml"


@singleton
class YamlSvc:
    def __init__(self):
        self.logger = BotFactoryLogger()
        self.answer_dict = self.load_yaml_to_dict(ANSWER_YAML)
        self.behaviour_dict = self.load_yaml_to_dict(BEHAVIOUR_YAML)
        self.qualities_flaws_dict = self.load_yaml_to_dict(QUALITIES_FLAWS)

    # Méthode 1: Avec un gestionnaire de contexte (recommandé)
    def load_yaml_to_dict(self, file_path):
        try:
            with open(file_path, "r") as file:
                yaml_dict = yaml.safe_load(file)
                self.logger.debug(f"Successfully loaded YAML file: {file_path}")
                return yaml_dict
        except Exception as e:
            self.logger.exception(f"Failed to load YAML file {file_path}: {e}")
            raise e
