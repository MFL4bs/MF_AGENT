from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    dynamodb_table_inventory: str = "mf_inventory"
    dynamodb_table_sessions: str = "mf_sessions"
    dynamodb_table_labor_prices: str = "mf_labor_prices"
    s3_bucket_products: str = "mf-products-images"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
