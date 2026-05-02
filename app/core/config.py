from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/knowledge_factory"

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_REQUEST_TIMEOUT_SECONDS: int = 15

    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ACTIVATION_TOKEN_EXPIRE_HOURS: int = 48
    RESET_TOKEN_EXPIRE_HOURS: int = 2

    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = ""
    ENVIRONMENT: str = "development"



    # --- SMTP / Outlook email settings ---
    # If SMTP_HOST + SMTP_USER + SMTP_PASSWORD are set, real emails will be sent.
    # Otherwise the notifier falls back to logging.
    SMTP_HOST: str = ""                       # e.g. smtp.office365.com
    SMTP_PORT: int = 587                      # 587 = STARTTLS, 465 = SSL
    SMTP_USER: str = ""                       # the mailbox you authenticate with
    SMTP_PASSWORD: str = ""                   # password OR app-password (if MFA on)
    SMTP_USE_TLS: bool = True                 # use STARTTLS (recommended for port 587)
    SMTP_USE_SSL: bool = False                # use SSL from the start (for port 465)
    EMAIL_FROM: str = ""                      # defaults to SMTP_USER
    EMAIL_FROM_NAME: str = "Knowledge Factory"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
