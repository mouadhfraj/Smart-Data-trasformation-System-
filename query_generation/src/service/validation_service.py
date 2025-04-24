
from typing import Dict, List


class QueryValidationService:
    """Service for validating dbt/SQLMesh model queries"""

    @staticmethod
    def validate_query(query: str) -> Dict[str, any]:
        """
        Validate a dbt/SQLMesh model query for syntax and best practices

        Args:
            query: SQL query string to validate

        Returns:
            Dictionary with:
            - is_valid: Boolean indicating overall validity
            - errors: List of error messages
            - warnings: List of warning messages
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        if not query:
            validation_result['errors'].append("Query is empty")
            validation_result['is_valid'] = False
            return validation_result


        normalized_query = query.upper().strip()


        QueryValidationService._validate_select_statement(normalized_query, validation_result)
        QueryValidationService._validate_no_dml_operations(normalized_query, validation_result)



        if validation_result['errors']:
            validation_result['is_valid'] = False

        return validation_result

    @staticmethod
    def _validate_select_statement(query: str, result: Dict[str, any]):
        """Validate the query contains a SELECT statement"""
        if "SELECT" not in query:
            result['errors'].append("Query must contain a SELECT statement")
            result['is_valid'] = False

    @staticmethod
    def _validate_no_dml_operations(query: str, result: Dict[str, any]):
        """Validate no DML operations are present"""
        dml_keywords = ["INSERT", "UPDATE", "DELETE", "TRUNCATE", "MERGE", "DROP"]
        for keyword in dml_keywords:
            if keyword in query:
                result['errors'].append(f"DML operation '{keyword}' not allowed in models")
                result['is_valid'] = False