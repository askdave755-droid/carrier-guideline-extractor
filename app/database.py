"""
Database connection and operations
"""
import asyncpg
import json
import os
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI


class Database:
    def __init__(self):
        self.pool = None
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("WARNING: OPENAI_API_KEY not set")
        self.openai = AsyncOpenAI(api_key=api_key, http_client=None)
        
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            os.getenv("DATABASE_URL"),
            min_size=5,
            max_size=20
        )
        print("Database connected")
        
    async def close(self):
        if self.pool:
            await self.pool.close()
            
    async def ensure_table(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                
                CREATE TABLE IF NOT EXISTS carrier_guidelines (
                    id SERIAL PRIMARY KEY,
                    carrier_name VARCHAR(100) NOT NULL,
                    line_of_business VARCHAR(50) DEFAULT 'commercial_auto',
                    state VARCHAR(2),
                    tier VARCHAR(20) DEFAULT 'standard',
                    content TEXT NOT NULL,
                    embedding VECTOR(1536),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_carrier_name ON carrier_guidelines(carrier_name);
                CREATE INDEX IF NOT EXISTS idx_carrier_vector ON carrier_guidelines USING ivfflat (embedding vector_cosine_ops);
            """)
            
    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000]
        )
        return response.data[0].embedding
        
    async def insert_guideline(self, carrier_name, line_of_business, state, tier, content, metadata):
        embedding = await self.generate_embedding(content)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO carrier_guidelines 
                (carrier_name, line_of_business, state, tier, content, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, carrier_name, line_of_business, state, tier, content, embedding, json.dumps(metadata))
            return row['id']
            
    async def get_carrier_rules(self, carrier, state):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT metadata FROM carrier_guidelines
                WHERE carrier_name = $1 AND state = $2
                LIMIT 1
            """, carrier, state)
            return json.loads(row['metadata']) if row else None


db = Database()
