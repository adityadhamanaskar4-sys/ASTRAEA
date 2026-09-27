import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class BackendConfig(BaseSettings):
    app_name: str = "ASTRAEA API & Data Flow Backend"
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Ledger Backend 2 integration settings
    ledger_db_path: str = os.getenv("ASTRAEA_LEDGER_DB", "astraea_ledger.db")
    node_id: str = os.getenv("ASTRAEA_NODE_ID", "NODE-ALPHA")
    node_key_hex: str = os.getenv("ASTRAEA_NODE_KEY", "A1B2C3D4E5F60718293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F90")
    
    # Storage settings (in-memory by default, ephemeral cache)
    in_memory_only: bool = True
    
    model_config = SettingsConfigDict(env_prefix="ASTRAEA_", case_sensitive=False)

config = BackendConfig()
