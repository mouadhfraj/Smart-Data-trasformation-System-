from logging import exception

from django.core.exceptions import ObjectDoesNotExist
from .models import GeneratedQuery


class GenerationRepository:

    def save_query_metadata(self, query_metadata_data, request=None):
        """
        Saves generated query metadata to the database

        Args:
            query_metadata_data (dict): Dictionary containing:
                - raw_query (str): The generated SQL query
                - prepared_prompt (str): The user's original prompt
                - llm_provider (str): The LLM provider used
                - generation_time_ms (int): Time taken to generate in ms
                - project_id (int): Associated project ID
            request (HttpRequest): Optional request object for user context

        Returns:
            GeneratedQuery: The created query object

        Raises:
            RepositoryError: If saving fails
        """
        try:


            query = GeneratedQuery.objects.create(
                raw_query=query_metadata_data['raw_query'],
                prepared_prompt=query_metadata_data['prepared_prompt'],
                llm_provider=query_metadata_data['llm_provider'],
                llm_parameters=query_metadata_data.get('llm_parameters', {}),
                generation_time_ms=query_metadata_data['generation_time_ms'],
                status='success',
                is_valid=False,
                user_id=1,
                project_id=query_metadata_data['project_id']
            )
            return query

        except KeyError as e:
            raise ValueError(f"Missing required field: {str(e)}")
        except Exception as e:
            raise exception(f"Failed to save query metadata: {str(e)}")

    def update_validation_status(self, query_id, is_valid):
        """
        Updates the validation status of a generated query

        Args:
            query_id (int): ID of the query to update
            is_valid (bool): Whether the query is valid

        Returns:
            GeneratedQuery: The updated query object

        Raises:
            RepositoryError: If update fails
        """
        try:
            query = GeneratedQuery.objects.get(query_id=query_id)
            query.is_valid = is_valid
            query.save()
            return query
        except ObjectDoesNotExist:
            raise exception(f"Query with ID {query_id} not found")
        except Exception as e:
            raise exception(f"Failed to update validation status: {str(e)}")