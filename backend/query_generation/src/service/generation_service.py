import os
import re
from typing import Dict, Any

from OpenSSL.rand import status
from langchain_groq import ChatGroq
from ..repo.models import LLMModel


class QueryGenerationService:

    @staticmethod
    def generate_query( prompt: str, metadata: Dict[str, Any], model: str) -> dict:
        """
        Generate SQL query using Groq's API with specified LLM

        Args:
            prompt: Natural language description of the query
            metadata: Dataset schema information
            model: One of 'mixtral-8x7b-32768', 'llama3-70b-8192', 'gemma-7b-it'...


        Returns:
            Generated SQL query string

        Raises:
            LLMGenerationError: If query generation fails
        """
        os.environ["GROQ_API_KEY"] = ""

        try:

            llmmodel = LLMModel.objects.get(name=model)

            schema_info = metadata.get('schema', {})
            database_type = metadata.get('database_type', '')

            system_prompt = f"""
            You are an expert SQL developer specialized in {database_type}. 
            Generate a syntactically correct SQL query based on the following context:
            1.Schema:{schema_info}
            2. User Request:{prompt}
            Guidelines:
            - Return ONLY the SQL query (no explanations or comments)
            - Use proper indentation and formatting
            - Use fully qualified table names if necessary (e.g., schema.table)
            - Follow {database_type} SQL syntax strictly
            - Include relevant WHERE, JOIN, GROUP BY, and ORDER BY clauses as appropriate
            - Ensure query is complete, accurate, and logically sound
            """

            llm = ChatGroq(
                model_name=llmmodel.model_code,
                temperature=llmmodel.default_temperature,
                api_key=os.getenv("GROQ_API_KEY"),

            )


            response = llm.invoke(system_prompt)



            generated_query = QueryGenerationService.extract_sql(response.content)




            return {
                'generated_query': generated_query,
                'prepared_prompt': system_prompt
            }

        except Exception as e:
            raise Exception(f"Query generation failed with {model}: {str(e)}")

    @staticmethod
    def extract_sql(response):
        """
        Cleans the SQL response by:
        1. Removing ```sql``` code blocks
        2. Removing any remaining ```
        3. Removing everything after the first semicolon (including the semicolon)
        4. Trimming whitespace

        Args:
            response (str): Raw SQL response string

        Returns:
            str: Cleaned SQL query without markdown formatting or semicolons

        Example:
            Input: "```sql\nSELECT * FROM users;\nUPDATE users SET...\n```"
            Output: "SELECT * FROM users"
        """

        cleaned = re.sub(r'```(?:sql)?\n?(.*?)\n?```', r'\1', response, flags=re.DOTALL)


        cleaned = cleaned.replace('```', '')


        cleaned = re.sub(r';.*', '', cleaned.strip())

        return cleaned.strip()