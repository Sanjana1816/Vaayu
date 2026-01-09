from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    This class loads environment variables from the .env file.
    Pydantic-settings handles the validation and type casting automatically.
    """
    database_url: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    openai_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()