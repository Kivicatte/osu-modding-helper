from pydantic_settings import BaseSettings, SettingsConfigDict, JsonConfigSettingsSource, PydanticBaseSettingsSource
import os


user_settings_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'resources', 'settings.json'))


class EditSettings(BaseSettings):
    deactivate_comment_on_scroll: bool = False
    stay_on_top: bool = False


class PlaytestSettings(BaseSettings):
    deactivate_comment_on_resume: bool = True
    merge_chain_misses: bool = True
    chain_miss_cooldown__ms: int = 1000


class SaveSettings(BaseSettings):
    ignore_empty_comments: bool = True
    ignore_default_miss_comments: bool = True
    output_file: str = 'comments.json'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        json_file=user_settings_file,
        json_file_encoding='utf-8',
    )

    edit_mode: EditSettings = EditSettings()
    playtest_mode: PlaytestSettings = PlaytestSettings()
    save_options: SaveSettings = SaveSettings()

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            JsonConfigSettingsSource(settings_cls)
        )


settings = Settings()


def reload(new_settings: BaseSettings | None = None):
    global settings
    settings = new_settings or Settings()
