import os
from crewai import Agent, Task, Crew, LLM
import boto3
import logging

# Configure logging for ECS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BedrockLLM(LLM):
    def __init__(self):
        super().__init__()
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body={
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "temperature": 0.1,
                    "max_tokens": 2048
                }
            )
            return response['body'].read().decode()
        except Exception as e:
            logger.error(f"Bedrock API Error: {str(e)}")
            raise

class SQLAgent:
    def __init__(self):
        self.llm = BedrockLLM()
        logger.info("Bedrock LLM initialized successfully")

    def generate_query(self, schema: str, question: str) -> str:
        try:
            sql_expert = Agent(
                role="Senior SQL Architect",
                goal="Generate perfect SQL queries matching exact schema requirements",
                backstory=(
                    "Expert in SQL with 15+ years experience creating optimized queries "
                    "for enterprise systems. Specializes in complex joins and subqueries."
                ),
                llm=self.llm,
                verbose=True
            )

            query_task = Task(
                description=f"""
                Generate a SQL query based on:
                - User Question: {question}
                - Database Schema: {schema}

                Requirements:
                1. Use EXACT table/column names from schema
                2. Maintain ANSI SQL-92 compatibility
                3. Include proper comments
                4. Validate query logic
                5. Optimize for performance
                """,
                expected_output="A perfect SQL query in code block format: ```sql\n...\n```",
                agent=sql_expert
            )

            crew = Crew(
                agents=[sql_expert],
                tasks=[query_task],
                verbose=2
            )

            result = crew.kickoff()
            logger.info("SQL query generated successfully")
            return result
        except Exception as e:
            logger.error(f"Query generation failed: {str(e)}")
            raise

if __name__ == "__main__":
    # Example schema and question
    schema = """
    CREATE TABLE employees (
        id INT PRIMARY KEY,
        name VARCHAR(100),
        department_id INT REFERENCES departments(id),
        hire_date DATE,
        salary DECIMAL(10,2)
    );

    CREATE TABLE departments (
        id INT PRIMARY KEY,
        name VARCHAR(50),
        budget DECIMAL(15,2)
    );
    """

    question = "Show department names with their total salary expenditure, ordered from highest to lowest"

    try:
        agent = SQLAgent()
        query = agent.generate_query(schema, question)
        print("\nGenerated SQL Query:")
        print(query)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        exit(1)
