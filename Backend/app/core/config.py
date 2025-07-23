from pydantic_settings import BaseSettings # type: ignore

class Settings(BaseSettings):
    SH_CLIENT_ID: str
    SH_CLIENT_SECRET: str

    class Config:
        env_file = ".env"

# Singleton instance you can import
settings = Settings()