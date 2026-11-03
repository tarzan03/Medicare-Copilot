from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):
    DB_CONNECTION: str
    GROQ_API_KEY: str
    LANGSMITH_API_KEY: str
    LANGSMITH_ENDPOINT: str
    LANGSMITH_PROJECT: str
    LANGSMITH_TRACING: str
    COHERE_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# if __name__ == "__main__":
#     print(settings.DB_CONNECTION)
