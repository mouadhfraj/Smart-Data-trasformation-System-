import os
import re


class QueryAdapter:
    @staticmethod
    def adapt_references(query: str, project_dir: str) -> str:
        """
        Replace table references with proper dbt ref() calls
        Args:
            query: Raw SQL query string
            project_dir: Path to project directory
        Returns:
            Query with references adapted
        """
        models_path = os.path.join(project_dir, "models")
        if not os.path.exists(models_path):
            return query


        existing_models = {
            os.path.splitext(f)[0].lower(): os.path.splitext(f)[0]
            for f in os.listdir(models_path)
            if f.endswith('.sql')
        }


        table_ref_pattern = re.compile(
            r'(?i)(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)(\s+|$|;|\))'
        )

        def replace_match(match):
            prefix = match.group(1)
            table = match.group(2).lower()
            suffix = match.group(3)


            if table in existing_models:
                return f"{prefix} {{{{ ref('{existing_models[table]}') }}}}{suffix}"
            return match.group(0)


        return table_ref_pattern.sub(replace_match, query)

    @staticmethod
    def adapt_sqlmesh_references(query: str, schema: str = "") -> str:
        """
        Ensure table references include schema prefix for SQLMesh when specified
        Args:
            query: Raw SQL query string
            schema: Schema name to use for references (optional, if empty no prefix is added)
        Returns:
            Query with references adapted for SQLMesh
        """
        # Pattern to match table references in FROM/JOIN clauses
        table_ref_pattern = re.compile(
            r'(?i)(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)(\s+|$|;|\))'
        )

        def replace_match(match):
            prefix = match.group(1)
            table = match.group(2)
            suffix = match.group(3)

            # Skip if already qualified
            if '.' in table:
                return match.group(0)

            # Add schema prefix only if specified
            if schema:
                return f"{prefix} {schema}.{table}{suffix}"
            return f"{prefix} {table}{suffix}"

        adapted_query = table_ref_pattern.sub(replace_match, query)
        QueryAdapter._warn_incompatible_dep(adapted_query)
        return adapted_query

    @staticmethod
    def _warn_incompatible_dep(query: str):
        """
        Check for SQLMesh incompatible references and warn about requirements.
        Args:
            query: The adapted query to check
        """
        # Pattern to find potentially problematic references
        invalid_ref_pattern = re.compile(
            r'(?i)(FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        )

        matches = invalid_ref_pattern.findall(query)
        if matches:
            for match in matches:
                print(f"Warning: Potential SQLMesh compatibility issue. "
                      f"Reference '{match[1]}' should use consistent qualification.")