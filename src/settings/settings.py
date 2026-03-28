from pydantic_settings import BaseSettings, SettingsConfigDict, JsonConfigSettingsSource, PydanticBaseSettingsSource
from pydantic import Field

from pathlib import Path
import os


user_settings_file = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'resources', 'settings.json'))


def _convert_field_title(name: str, info):
    match name.split('__'):
        case [name]:
            return name.replace('_', ' ').capitalize()
        case [name, unit]:
            return f"{name.replace('_', ' ').capitalize()} ({unit.replace('_', ' ')})"


class EditSettings(BaseSettings):
    model_config = SettingsConfigDict(
        field_title_generator=_convert_field_title
    )

    deactivate_comment_on_scroll: bool = False
    stay_on_top: bool = False


class PlaytestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        field_title_generator=_convert_field_title
    )

    deactivate_comment_on_resume: bool = True
    merge_chain_misses: bool = True
    chain_miss_cooldown__ms: int = Field(default=1000, gt=0, le=10000)


class SaveSettings(BaseSettings):
    model_config = SettingsConfigDict(
        field_title_generator=_convert_field_title
    )

    ignore_empty_comments: bool = True
    ignore_default_miss_comments: bool = True
    output_file: Path = 'comments.json'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        json_file=user_settings_file,
        json_file_encoding='utf-8',
        field_title_generator=_convert_field_title
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
