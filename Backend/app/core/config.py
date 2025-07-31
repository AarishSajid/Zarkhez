from pydantic_settings import BaseSettings # type: ignore

class Settings(BaseSettings):
    SH_CLIENT_ID: str
    SH_CLIENT_SECRET: str
    jwt_secret: str
    database_url: str
    openweather: str 
    weather_url: str 
    disease_model_path: str

    class Config:
        env_file = ".env"

# Singleton instance you can import
settings = Settings()